"""Synthetic safety regressions for fallback and archive boundaries."""
import os
import tarfile

from blackbox.config import Config
from blackbox.store import Catalog
from blackbox.why.archive_read import extract_day
from blackbox.why.evidence import collect_boot
from blackbox.why import archive_read


def test_archive_rejects_excess_members_without_getmembers(tmp_path, monkeypatch):
    cfg = Config(ssd_root=str(tmp_path / "ssd"),
                 hdd_archive_root=str(tmp_path / "hdd"))
    os.makedirs(os.path.join(cfg.ssd_root, "tmp"))
    os.makedirs(os.path.join(cfg.hdd_archive_root, "2026"))
    archive = os.path.join(cfg.hdd_archive_root, "2026",
                           "blackbox-2026-W40.tar.xz")
    with tarfile.open(archive, "w:xz") as tar:
        for index in range(archive_read.MAX_MEMBERS + 1):
            info = tarfile.TarInfo("2026-10-01/unused-%d" % index)
            info.size = 0
            import io
            tar.addfile(info, io.BytesIO(b""))
    monkeypatch.setattr(tarfile.TarFile, "getmembers",
                        lambda self: (_ for _ in ()).throw(AssertionError()))
    path, reason = extract_day(cfg, {"path": archive}, "2026-10-01")
    assert path is None and reason


def test_duplicate_selected_path_rejected(tmp_path):
    cfg = Config(ssd_root=str(tmp_path / "ssd"),
                 hdd_archive_root=str(tmp_path / "hdd"))
    os.makedirs(os.path.join(cfg.ssd_root, "tmp"))
    os.makedirs(os.path.join(cfg.hdd_archive_root, "2026"))
    archive = os.path.join(cfg.hdd_archive_root, "2026",
                           "blackbox-2026-W40.tar.xz")
    import io
    with tarfile.open(archive, "w:xz") as tar:
        for value in (b"a", b"b"):
            info = tarfile.TarInfo("2026-10-01/journal.log")
            info.size = 1
            tar.addfile(info, io.BytesIO(value))
    path, reason = extract_day(cfg, {"path": archive}, "2026-10-01")
    assert path is None and reason


def test_boot_rows_merge_closed_fallback_with_ssd_active_cursor(tmp_path):
    cfg = Config(ssd_root=str(tmp_path / "ssd"),
                 fallback_root=str(tmp_path / "fallback"))
    os.makedirs(cfg.ssd_root)
    os.makedirs(cfg.fallback_root)
    active = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    active.upsert_boot({"boot_id": "current", "start": 1791765000,
                        "end": None, "clean": None, "last_heartbeat": None,
                        "reset_source": None, "pstore": [], "verdict": None,
                        "confidence": None})
    active.set_cursor("active_boot", "current")
    active.close()
    previous = Catalog(os.path.join(cfg.fallback_root, "catalog.db"))
    previous.upsert_boot({"boot_id": "previous", "start": 1791757480,
                          "end": 1791763680, "clean": False,
                          "last_heartbeat": 1791763670, "reset_source": "unknown",
                          "pstore": [], "verdict": None, "confidence": None})
    previous.close()
    assert collect_boot(cfg, -1).boot["boot_id"] == "previous"
