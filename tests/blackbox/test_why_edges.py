"""Synthetic boundary tests for read-only why evidence."""
import json
import os
import tarfile

from blackbox.config import Config
from blackbox.store import Catalog
from blackbox.why.evidence import collect_boot
from blackbox.why import evidence as evidence_module
from blackbox.why.archive_read import extract_day
from blackbox.why.evidence import collect
from blackbox.why.journal_read import normalize_line


def _cfg(root):
    return Config(ssd_root=str(root / "ssd"), fallback_root=str(root / "fallback"),
                  hdd_archive_root=str(root / "hdd"), ssd_mount=str(root / "ssd"))


def test_empty_hot_root_is_read_only_and_does_not_create_db(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.ssd_root)
    ev = collect(cfg, 1790812800, 1790899200)
    assert ev.samples == [] and ev.events == []
    assert not os.path.exists(os.path.join(cfg.ssd_root, "catalog.db"))
    assert not os.path.exists(os.path.join(cfg.ssd_root, "hot"))


def test_fallback_catalog_events_are_read_without_writes(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.fallback_root)
    cat = Catalog(os.path.join(cfg.fallback_root, "catalog.db"))
    cat.add_events([{"ts": 1790813000, "source": "docker", "kind": "die",
                     "subject": "homecloud_stt", "severity": "crit",
                     "detail": {"exitCode": 137}}])
    cat.close()
    before = os.path.getsize(os.path.join(cfg.fallback_root, "catalog.db"))
    ev = collect(cfg, 1790812800, 1790899200, "homecloud_stt")
    assert len(ev.events) == 1
    assert os.path.getsize(os.path.join(cfg.fallback_root, "catalog.db")) == before


def test_archive_member_path_rejected_and_temp_cleaned(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(os.path.join(cfg.hdd_archive_root, "2026"))
    os.makedirs(cfg.ssd_root)
    archive = os.path.join(cfg.hdd_archive_root, "2026", "blackbox-2026-W40.tar.xz")
    with tarfile.open(archive, "w:xz") as tf:
        source = tmp_path / "payload"
        source.write_text("synthetic", encoding="utf-8")
        tf.add(str(source), arcname="2026-10-01/../../escape")
    row = {"path": archive, "sha256": ""}
    path, reason = extract_day(cfg, row, "2026-10-01")
    assert path is None and reason
    assert not os.path.exists(os.path.join(cfg.ssd_root, "tmp")) or not os.listdir(
        os.path.join(cfg.ssd_root, "tmp"))


def test_week_archive_skips_other_safe_days_and_extracts_requested_day(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(os.path.join(cfg.hdd_archive_root, "2026"))
    os.makedirs(os.path.join(cfg.ssd_root, "tmp"))
    archive = os.path.join(cfg.hdd_archive_root, "2026", "blackbox-2026-W40.tar.xz")
    with tarfile.open(archive, "w:xz") as tf:
        for day in ("2026-09-28", "2026-10-01"):
            source = tmp_path / (day + ".txt")
            source.write_text("synthetic", encoding="utf-8")
            tf.add(str(source), arcname=day + "/journal.log")
    path, reason = extract_day(cfg, {"path": archive}, "2026-10-01")
    assert reason is None
    assert os.path.isfile(os.path.join(path, "journal.log"))


def test_hot_journal_is_read_from_day_directory_not_nested_day(tmp_path):
    cfg = _cfg(tmp_path)
    day = "2026-10-01"
    hot = tmp_path / "ssd" / "hot" / day
    hot.mkdir(parents=True)
    (hot / "journal.log").write_text(
        "2026-10-01T00:00:05+0000 host kernel: synthetic event\n", encoding="utf-8")
    start = 1790812800
    ev = collect(cfg, start, start + 86400)
    assert ev.journal and "synthetic event" in ev.journal[0][1]


def test_degraded_collect_uses_fallback_only(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.ssd_root)
    os.makedirs(cfg.fallback_root)
    Catalog(os.path.join(cfg.ssd_root, "catalog.db")).close()
    cat = Catalog(os.path.join(cfg.fallback_root, "catalog.db"))
    cat.add_events([{"ts": 1790813000, "source": "docker", "kind": "die",
                     "subject": "homecloud_stt", "severity": "crit", "detail": {}}])
    cat.close()
    ev = collect(cfg, 1790812800, 1790899200, ssd_available=False)
    assert len(ev.events) == 1
    assert any("SSD unavailable" in reason for reason in ev.reasons)


def test_short_iso_timestamp_and_logger_normalized():
    stamp, line = normalize_line(
        "2026-10-12T03:30:01.123456+0000 jetson dockerd[900]: healthy")
    assert stamp == 1791775801
    assert line == "dockerd: healthy"


def test_synthetic_collect_never_runs_live_journalctl(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(evidence_module.time, "time", lambda: 1500)

    def forbidden(*args, **kwargs):
        raise AssertionError("direct collect must be synthetic/read-only")

    monkeypatch.setattr(evidence_module.subprocess, "run", forbidden)
    ev = collect(cfg, 1000, 2000, live=False)
    assert ev.journal == []


def test_worker_live_journal_normalizes_and_filters(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(evidence_module.time, "time", lambda: 1500)

    class Result(object):
        returncode = 0
        stdout = (b"1970-01-01T00:25:00+0000 host dockerd[22]: homecloud_stt restarted\n"
                  b"1970-01-01T00:25:01+0000 host dockerd[22]: homecloud_nextcloud restarted\n")

    monkeypatch.setattr(evidence_module.subprocess, "run", lambda *a, **k: Result())
    ev = collect(cfg, 1000, 2000, container="homecloud_stt", live=True)
    assert ev.journal == [(1500, "dockerd: homecloud_stt restarted")]


def test_corrupt_hot_sqlite_is_unknown_reason_not_healthy(tmp_path):
    cfg = _cfg(tmp_path)
    path = tmp_path / "ssd" / "hot" / "2026-10-01" / "metrics.db"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not sqlite")
    ev = collect(cfg, 1790812800, 1790899200)
    assert ev.samples == []
    assert ev.reasons


def test_previous_boot_uses_associated_current_snapshot(tmp_path):
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.ssd_root)
    cat = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    cat.upsert_boot({"boot_id": "previous", "start": 1791757480,
                     "end": 1791763680, "clean": False,
                     "last_heartbeat": 1791763670, "reset_source": "unknown",
                     "pstore": [], "verdict": None, "confidence": None})
    cat.upsert_boot({"boot_id": "current", "start": 1791765000,
                     "end": None, "clean": None, "last_heartbeat": None,
                     "reset_source": None, "pstore": [], "verdict": None,
                     "confidence": None})
    cat.set_cursor("active_boot", "current")
    cat.set_cursor("boot-snapshot:previous", "current")
    snap = tmp_path / "ssd" / "boots" / "current"
    (snap / "pstore").mkdir(parents=True)
    (snap / "summary.json").write_text(json.dumps(
        {"boot_id": "current", "ts": 1791765000, "pstore": ["panic.txt"],
         "mounts": {"/mnt/hdd2tb": "disk-a"}, "disks": {"disk-a": {"mountpoint": "/mnt/hdd2tb"}}}), encoding="utf-8")
    (snap / "pstore" / "panic.txt").write_text("synthetic panic", encoding="utf-8")
    (snap / "prev_journal_tail.txt").write_text(
        "2026-10-12T03:30:01+0000 jetson kernel: synthetic previous boot\n", encoding="utf-8")
    ev = collect_boot(cfg, -1)
    assert ev.boot["boot_id"] == "previous"
    assert ev.pstore == ["panic.txt"]
    assert ev.snapshots[0]["boot_id"] == "current"
    assert ev.journal and "synthetic previous boot" in ev.journal[0][1]
    cat.close()
