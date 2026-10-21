"""Catalog integration for boot snapshot records; synthetic configured paths only."""
import json
import os

import pytest

from blackbox import boot_record, bootsnap
from blackbox.config import Config
from blackbox.store import Catalog, write_heartbeat

NOW = 2000000000
CURRENT = "boot_current"
PREVIOUS = "boot_previous"


def _cfg(tmp_path):
    ssd, fallback, proc = tmp_path / "ssd", tmp_path / "fallback", tmp_path / "proc"
    for path in (ssd, fallback, proc):
        path.mkdir()
    return Config(ssd_root=str(ssd), ssd_mount=str(tmp_path),
                  fallback_root=str(fallback), proc_root=str(proc))


def _snapshot(root, boot_id, ts):
    path = root / "boots" / boot_id
    path.mkdir(parents=True)
    (path / "summary.json").write_text(json.dumps({
        "boot_id": boot_id, "ts": ts, "pstore": ["ramoops"]}), encoding="utf-8")
    (path / "prev_journal_tail.txt").write_text(
        "systemd-shutdown: Reached target Power-Off.\n", encoding="utf-8")
    (path / "reset_source.txt").write_text("reset: test\n", encoding="utf-8")
    return str(path)


def _proc(cfg, btime=1900000000):
    with open(os.path.join(cfg.proc_root, "stat"), "w", encoding="ascii") as fh:
        fh.write("cpu 1 2 3\nbtime %d\n" % btime)


def _catalog(root):
    return Catalog(os.path.join(str(root), "catalog.db"))


def test_transition_records_previous_and_current_boot(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, "ismount", lambda _path: True)
    snap = _snapshot(tmp_path / "ssd", CURRENT, NOW - 0.25)
    _proc(cfg)
    write_heartbeat(os.path.join(cfg.fallback_root, "heartbeat"), PREVIOUS,
                    NOW - 20, {})
    catalog = _catalog(tmp_path / "ssd")
    catalog.upsert_boot({"boot_id": PREVIOUS, "start": 1800000000,
                         "verdict": "old", "confidence": "low"})
    catalog.close()

    boot_record.record_boot(cfg, CURRENT, snap, NOW)

    catalog = _catalog(tmp_path / "ssd")
    previous = catalog.get_boot(PREVIOUS)
    current = catalog.get_boot(CURRENT)
    assert previous["start"] == 1800000000
    assert bool(previous["clean"]) is True
    assert previous["last_heartbeat"] == NOW - 20
    assert previous["verdict"] is None and previous["confidence"] is None
    assert current["start"] == 1900000000 and current["end"] is None
    assert current["clean"] is None
    assert catalog.get_cursor("active_boot") == CURRENT
    assert catalog.get_cursor("boot-snapshot:" + PREVIOUS) == CURRENT
    catalog.close()


def test_unknown_previous_id_does_not_borrow_unrelated_catalog_start(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, "ismount", lambda _path: True)
    snap = _snapshot(tmp_path / "ssd", CURRENT, NOW)
    _proc(cfg)
    write_heartbeat(os.path.join(cfg.fallback_root, "heartbeat"), PREVIOUS,
                    NOW - 10, {})
    catalog = _catalog(tmp_path / "ssd")
    catalog.upsert_boot({"boot_id": "unrelated", "start": 1234})
    catalog.close()

    boot_record.record_boot(cfg, CURRENT, snap, NOW)

    catalog = _catalog(tmp_path / "ssd")
    row = catalog.get_boot(PREVIOUS)
    assert row["boot_id"] == PREVIOUS and row["start"] is None
    assert catalog.get_boot("unrelated")["start"] == 1234
    catalog.close()


def test_retry_with_current_heartbeat_preserves_previous_verdict_and_start(
        tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, "ismount", lambda _path: True)
    snap = _snapshot(tmp_path / "ssd", CURRENT, NOW)
    _proc(cfg, 1900000000)
    write_heartbeat(os.path.join(cfg.fallback_root, "heartbeat"), PREVIOUS,
                    NOW - 30, {})
    write_heartbeat(os.path.join(cfg.fallback_root, "current-heartbeat"),
                    CURRENT, NOW - 1, {})
    # Put the current heartbeat at its configured canonical path.
    os.replace(os.path.join(cfg.fallback_root, "current-heartbeat"),
               os.path.join(cfg.fallback_root, "heartbeat.current"))
    # Current heartbeat is supplied through the SSD source for this retry.
    write_heartbeat(os.path.join(cfg.ssd_root, "heartbeat"), CURRENT,
                    NOW - 1, {})
    catalog = _catalog(tmp_path / "ssd")
    catalog.upsert_boot({"boot_id": PREVIOUS, "start": 1800000000,
                         "verdict": "probable", "confidence": "high"})
    catalog.upsert_boot({"boot_id": CURRENT, "start": 1700000000})
    catalog.set_cursor("active_boot", CURRENT)
    catalog.close()

    boot_record.record_boot(cfg, CURRENT, snap, NOW)

    catalog = _catalog(tmp_path / "ssd")
    assert catalog.get_boot(PREVIOUS)["verdict"] == "probable"
    assert catalog.get_boot(CURRENT)["start"] == 1700000000
    catalog.close()


def test_fallback_snapshot_uses_fallback_catalog_and_ignores_unmounted_ssd(
        tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, "ismount", lambda _path: False)
    snap = _snapshot(tmp_path / "fallback", CURRENT, NOW)
    _proc(cfg)
    write_heartbeat(os.path.join(cfg.fallback_root, "heartbeat"), PREVIOUS,
                    NOW - 50, {})
    write_heartbeat(os.path.join(cfg.ssd_root, "heartbeat"), "ssd_old",
                    NOW - 1, {})

    boot_record.record_boot(cfg, CURRENT, snap, NOW)

    catalog = _catalog(tmp_path / "fallback")
    assert catalog.get_boot(PREVIOUS)["last_heartbeat"] == NOW - 50
    assert catalog.get_boot("ssd_old") is None
    catalog.close()
    assert not os.path.exists(os.path.join(cfg.ssd_root, "catalog.db"))


def test_previous_boot_summary_unknown_heartbeat_id_has_no_wrong_start(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.upsert_boot({"boot_id": "other", "start": 55})
    summary = bootsnap.previous_boot_summary(
        catalog, {"boot_id": PREVIOUS, "ts": NOW - 1}, [], [], None)
    assert summary["boot_id"] == PREVIOUS and summary["start"] is None
    catalog.close()


def test_snapshot_path_and_summary_size_are_guarded(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, "ismount", lambda _path: True)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(OSError, match="snapshot path rejected"):
        boot_record.record_boot(cfg, CURRENT, str(outside), NOW)
    snap = _snapshot(tmp_path / "ssd", CURRENT, NOW)
    with open(os.path.join(snap, "summary.json"), "w", encoding="utf-8") as fh:
        fh.write(" " * (boot_record.SUMMARY_LIMIT + 1))
    with pytest.raises(OSError, match="unsafe or oversized"):
        boot_record.record_boot(cfg, CURRENT, snap, NOW)
