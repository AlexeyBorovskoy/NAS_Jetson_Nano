"""Краевые проверки archive worker, путей и безопасной передачи данных."""
import hashlib
import os
import shutil

import pytest

from blackbox import archive
from blackbox.config import Config
from blackbox.store import Catalog


class _Completed(object):
    def __init__(self, code=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = code, stdout, stderr


class _Run(object):
    def __init__(self, fail=None):
        self.fail = fail

    def __call__(self, args, **kwargs):
        parts = list(args)
        command = parts[parts.index("cp")] if "cp" in parts else None
        if self.fail == command:
            return _Completed(1, stderr="password=must-not-escape")
        if command:
            shutil.copyfile(parts[-2], parts[-1])
        if "sha256sum" in parts:
            with open(parts[-1], "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            return _Completed(0, digest + "  " + parts[-1] + "\n")
        if "stat" in parts:
            return _Completed(0)
        if "systemctl" in parts:
            return _Completed(3)
        if "pgrep" in parts:
            return _Completed(1)
        return _Completed(0)


def _cfg(tmp_path):
    mount = tmp_path / "hdd"
    mount.mkdir()
    root = mount / "backups" / "blackbox"
    root.mkdir(parents=True)
    return Config(ssd_root=str(tmp_path / "ssd"),
                  hdd_mount=str(mount), hdd_archive_root=str(root))


def _week_hot(root, days):
    for day in days:
        path = root / day
        path.mkdir(parents=True)
        (path / "sample.bin").write_bytes(day.encode("ascii"))


@pytest.mark.parametrize("week", ["../2026-W40", "2026-W00", "2021-W53", "2026-W1"])
def test_build_rejects_invalid_or_noncalendar_week(tmp_path, week):
    hot, stage = tmp_path / "hot", tmp_path / "stage"
    hot.mkdir()
    stage.mkdir()
    with pytest.raises(ValueError):
        archive.build_archive(str(hot), week, str(stage))
    assert list(stage.iterdir()) == []


def test_weeks_due_ignores_invalid_and_current_week_directories(tmp_path):
    hot = tmp_path / "hot"
    _week_hot(hot, ["2026-10-04", "2026-10-11", "2026-10-13"])
    (hot / "2026-99-99").mkdir()
    (hot / ".hidden").mkdir()
    assert archive.weeks_due(str(hot), "2026-10-13") == ["2026-W40"]


def test_build_refuses_symlink_in_week_and_keeps_source(tmp_path):
    hot, stage = tmp_path / "hot", tmp_path / "stage"
    _week_hot(hot, ["2026-10-01"])
    stage.mkdir()
    target = tmp_path / "outside"
    target.write_text("owner data", encoding="utf-8")
    try:
        os.symlink(str(target), str(hot / "2026-10-01" / "linked"))
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(OSError, match="archive: build failed"):
        archive.build_archive(str(hot), "2026-W40", str(stage))
    assert target.read_text(encoding="utf-8") == "owner data"
    assert (hot / "2026-10-01" / "sample.bin").exists()


def test_build_preserves_preexisting_staging_temp(tmp_path):
    hot, stage = tmp_path / "hot", tmp_path / "stage"
    _week_hot(hot, ["2026-10-01"])
    stage.mkdir()
    temp = stage / "blackbox-2026-W40.tar.xz.tmp"
    temp.write_bytes(b"owner artifact")
    with pytest.raises(OSError, match="staging temp exists"):
        archive.build_archive(str(hot), "2026-W40", str(stage))
    assert temp.read_bytes() == b"owner artifact"


def test_failed_copy_keeps_hot_day_and_hides_stderr(tmp_path):
    cfg = _cfg(tmp_path)
    catalog = Catalog(str(tmp_path / "catalog.db"))
    os.makedirs(os.path.join(cfg.ssd_root, "staging"))
    hot = tmp_path / "ssd" / "hot"
    _week_hot(hot, ["2026-10-01"])
    result = archive.archive_week(cfg, catalog, "2026-W40", _Run(fail="cp"))
    assert result == {"status": "failed", "reason": archive.FIXED_ERROR}
    assert (hot / "2026-10-01" / "sample.bin").exists()
    assert not list((tmp_path / "hdd").rglob("*.tmp"))
    catalog.close()


def test_worker_mount_guard_precedes_catalog_and_hdd_work(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(archive, "load_config", lambda: cfg)
    monkeypatch.setattr(archive.os.path, "ismount", lambda _path: False)
    monkeypatch.setattr("blackbox.archive_supervisor.await_worker_authorization",
                        lambda *_args: True)
    monkeypatch.setattr("blackbox.archive_supervisor.worker_marker_path",
                        lambda _cfg: "unused")
    monkeypatch.setattr(archive, "Catalog",
                        lambda *_args: (_ for _ in ()).throw(AssertionError("catalog opened")))
    assert archive.worker_main() == 3
