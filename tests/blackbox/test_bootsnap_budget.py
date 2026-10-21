"""Synthetic bootsnap contract and capacity regressions."""
import os
import pytest
from blackbox import bootsnap
from blackbox.bootsnap import take_snapshot
from test_bootsnap_edges import _cfg, _Run, _read


def _tree_file_bytes(root):
    total = 0
    for directory, _dirs, files in os.walk(str(root), followlinks=False):
        for name in files:
            path = os.path.join(directory, name)
            if not os.path.islink(path):
                total += os.path.getsize(path)
    return total


def _force_fallback(cfg, root):
    cfg.ssd_mount = os.path.join(str(root), "not-mounted")


def test_snapshot_respects_aggregate_budget(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    _force_fallback(cfg, tmp_path)
    monkeypatch.setattr(bootsnap, "SNAPSHOT_MAX_BYTES", 4096)
    monkeypatch.setattr(bootsnap, "TEXT_AGGREGATE_BYTES", 2048)
    monkeypatch.setattr(bootsnap, "PSTORE_AGGREGATE_BYTES", 2048)
    monkeypatch.setattr(bootsnap, "SNAPSHOT_META_RESERVE", 1024)
    monkeypatch.setattr(bootsnap, "MIN_SNAPSHOT_BUDGET", 2048)
    cfg.fallback_cap_bytes = 4096
    (tmp_path / "sys" / "fs" / "pstore" / "dump").write_bytes(b"P" * 4096)
    run = _Run(outputs={key: "x" * 2000 for key in
                        ("uname", "nv_tegra_release", "dmesg", "lsblk",
                         "by-id", "lsusb", "journalctl", "docker")})

    snap = take_snapshot(cfg, "boot-cap", run=run, now=lambda: 15)

    assert _tree_file_bytes(cfg.fallback_root) <= cfg.fallback_cap_bytes
    assert "truncated" in _read(snap, "uname.txt")
    assert os.path.isfile(os.path.join(str(snap), "pstore", "dump.truncated"))


def test_fallback_budget_counts_existing_files_and_preserves_them(tmp_path):
    cfg = _cfg(tmp_path)
    _force_fallback(cfg, tmp_path)
    cfg.fallback_cap_bytes = 32
    old = tmp_path / "fallback" / "old.bin"
    old.parent.mkdir()
    old.write_bytes(b"keep-me" * 5)

    with pytest.raises(OSError, match="bootsnap: недостаточный бюджет снимка"):
        take_snapshot(cfg, "boot-no-room", run=_Run(), now=lambda: 16)

    assert old.read_bytes() == b"keep-me" * 5
    assert not os.path.exists(os.path.join(cfg.fallback_root, "boots",
                                           "boot-no-room", "summary.json"))


def test_repeated_fallback_snapshot_replaces_known_files_within_cap(tmp_path):
    cfg = _cfg(tmp_path)
    _force_fallback(cfg, tmp_path)
    cfg.fallback_cap_bytes = 1024 * 1024
    run = _Run(outputs={"uname": "Linux jetson\n"})

    first = take_snapshot(cfg, "same-boot", run=run, now=lambda: 17)
    size_after_first = _tree_file_bytes(cfg.fallback_root)
    second = take_snapshot(cfg, "same-boot", run=run, now=lambda: 18)

    assert str(first) == str(second)
    assert _tree_file_bytes(cfg.fallback_root) == size_after_first
