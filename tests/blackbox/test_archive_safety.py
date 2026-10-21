"""Task 9 immutable-archive safety regressions using synthetic paths and commands."""
import hashlib
import os
import shutil
import sqlite3

from blackbox import archive
from blackbox.config import Config
from blackbox.store import Catalog


class _Result(object):
    def __init__(self, code=0, stdout=""):
        self.returncode, self.stdout = code, stdout


class _Run(object):
    def __call__(self, argv, **kwargs):
        parts = list(argv)
        if "systemctl" in parts:
            return _Result(3)
        if "pgrep" in parts:
            return _Result(1)
        if "stat" in parts:
            return _Result(0)
        if "cp" in parts:
            shutil.copyfile(parts[-2], parts[-1])
        if "sha256sum" in parts:
            with open(parts[-1], "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            return _Result(0, digest + "  " + parts[-1] + "\n")
        return _Result(0)


def _case(tmp_path):
    ssd, hot, stage = tmp_path / "ssd", tmp_path / "ssd" / "hot", tmp_path / "ssd" / "staging"
    hdd = tmp_path / "hdd"
    for path in (hot, stage, hdd / "backups" / "blackbox"):
        path.mkdir(parents=True, exist_ok=True)
    day = hot / "2026-10-01"
    day.mkdir()
    data = day / "sample.bin"
    data.write_bytes(b"original")
    cfg = Config(ssd_root=str(ssd), hdd_mount=str(hdd),
                 hdd_archive_root=str(hdd / "backups" / "blackbox"))
    return cfg, data


def _catalog(tmp_path):
    return Catalog(str(tmp_path / "ssd" / "catalog.db"))


def test_ship_keeps_existing_different_archive_immutable(tmp_path):
    stage, hdd = tmp_path / "stage", tmp_path / "hdd"
    stage.mkdir()
    hdd.mkdir()
    source = stage / "blackbox-2026-W40.tar.xz"
    source.write_bytes(b"new verified data")
    final = hdd / source.name
    final.write_bytes(b"old verified data")
    old = final.read_bytes()
    sha = hashlib.sha256(source.read_bytes()).hexdigest()

    assert archive.ship(str(source), sha, str(hdd), _Run()) is False
    assert final.read_bytes() == old
    assert not (hdd / (source.name + ".sha256")).exists()


def test_ship_verifies_temp_before_promoting(tmp_path):
    stage, hdd = tmp_path / "stage", tmp_path / "hdd"
    stage.mkdir()
    hdd.mkdir()
    source = stage / "blackbox-2026-W40.tar.xz"
    source.write_bytes(b"payload")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()

    class WrongHash(_Run):
        def __call__(self, argv, **kwargs):
            if "sha256sum" in argv:
                return _Result(0, "0" * 64 + "  temp\n")
            return super().__call__(argv, **kwargs)

    assert archive.ship(str(source), sha, str(hdd), WrongHash()) is False
    assert not (hdd / source.name).exists()
    assert list(hdd.iterdir()) == []


def test_ship_reuses_matching_existing_archive_without_replacement(tmp_path):
    stage, hdd = tmp_path / "stage", tmp_path / "hdd"
    stage.mkdir()
    hdd.mkdir()
    source = stage / "blackbox-2026-W40.tar.xz"
    source.write_bytes(b"same data")
    final = hdd / source.name
    final.write_bytes(source.read_bytes())
    expected = final.read_bytes()
    sha = hashlib.sha256(expected).hexdigest()

    assert archive.ship(str(source), sha, str(hdd), _Run()) is True
    assert final.read_bytes() == expected
    assert (hdd / (source.name + ".sha256")).read_text(encoding="ascii") == (
        sha + "  " + source.name + "\n")


def test_busy_check_unknown_defers_and_source_mutation_is_retained(tmp_path, monkeypatch):
    cfg, source = _case(tmp_path)
    catalog = _catalog(tmp_path)

    class Unknown(_Run):
        def __call__(self, argv, **kwargs):
            return _Result(4) if "systemctl" in argv else super().__call__(argv, **kwargs)

    result = archive.archive_week(cfg, catalog, "2026-W40", Unknown())
    assert result["status"] == "deferred" and "busycheck_failed" in result["reason"]

    original = archive.build_archive
    def mutate_after_build(*args):
        built = original(*args)
        source.write_bytes(b"changed during snapshot")
        return built
    monkeypatch.setattr(archive, "build_archive", mutate_after_build)
    result = archive.archive_week(cfg, catalog, "2026-W40", _Run())
    assert result["status"] == "failed" and result["reason"] == "source changed"
    assert source.exists() and catalog.archives() == []
    catalog.close()


def test_catalog_conflict_and_commit_failure_keep_hot_source(tmp_path, monkeypatch):
    cfg, source = _case(tmp_path)
    catalog = _catalog(tmp_path)
    catalog.add_archive({"week": "2026-W40", "path": "old", "sha256": "f" * 64,
                         "first_day": "2026-10-01", "last_day": "2026-10-01",
                         "created": 1, "verified": True})
    result = archive.archive_week(cfg, catalog, "2026-W40", _Run())
    assert result["status"] == "failed" and source.exists()
    assert not list((tmp_path / "hdd").rglob("*.tar.xz"))
    catalog.close()

    base = tmp_path / "commit-failure"
    base.mkdir()
    cfg, source = _case(base)
    catalog = _catalog(base)
    monkeypatch.setattr(catalog, "add_archive",
                        lambda _row: (_ for _ in ()).throw(sqlite3.OperationalError("db")))
    result = archive.archive_week(cfg, catalog, "2026-W40", _Run())
    assert result["status"] == "failed" and source.exists()
    catalog.close()


def test_worker_returns_failure_when_any_due_week_fails(tmp_path, monkeypatch):
    cfg, _source = _case(tmp_path)
    class FakeCatalog(object):
        def __init__(self, _path): pass
        def close(self): pass
    monkeypatch.setattr(archive, "load_config", lambda: cfg)
    monkeypatch.setattr(archive, "Catalog", FakeCatalog)
    monkeypatch.setattr(archive.os.path, "ismount", lambda _path: True)
    monkeypatch.setattr("blackbox.archive_supervisor.await_worker_authorization",
                        lambda *_args: True)
    monkeypatch.setattr("blackbox.archive_supervisor.worker_marker_path",
                        lambda _cfg: "unused")
    monkeypatch.setattr(archive, "weeks_due", lambda *_args: ["2026-W40"])
    monkeypatch.setattr(archive, "archive_week",
                        lambda *_args: {"status": "failed", "reason": archive.FIXED_ERROR})
    monkeypatch.setattr(archive, "hdd_busy", lambda *_args: "busycheck_failed")

    assert archive.worker_main() == 5
