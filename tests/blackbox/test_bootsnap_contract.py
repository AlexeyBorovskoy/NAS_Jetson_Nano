"""Synthetic bootsnap contract and capacity regressions."""
import os
import pytest
from blackbox import bootsnap
from blackbox.bootsnap import take_snapshot
from test_bootsnap_edges import _cfg, _Run, _read


def test_disk_mapping_uses_deterministic_whole_disk_alias(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    by_id = os.path.join(cfg.dev_root, "disk", "by-id")
    os.makedirs(by_id)
    aliases = ["wwn-z", "ata-a", "ata-a-part1", "usb-z"]
    for alias in aliases:
        open(os.path.join(by_id, alias), "w").close()
    real_islink = os.path.islink
    monkeypatch.setattr(bootsnap.os.path, "islink",
                        lambda path: path.startswith(by_id) or real_islink(path))
    monkeypatch.setattr(bootsnap.os, "readlink", lambda path:
                        "../../sdb" if path.startswith(by_id) else "")

    (tmp_path / "proc" / "mounts").write_text(
        "/dev/sdb1 /mnt/hdd2tb fuseblk rw 0 0\n", encoding="utf-8")
    snap = take_snapshot(cfg, "boot-map", run=_Run(), now=lambda: 13)

    import json
    with open(os.path.join(str(snap), "summary.json"), encoding="utf-8") as fh:
        summary = json.load(fh)
    assert summary["disks"] == {"sdb": "usb-z"}
    assert summary["mounts"] == {"/mnt/hdd2tb": "usb-z"}


def test_journal_and_command_text_mask_family_url_and_space_secrets(tmp_path):
    cfg = _cfg(tmp_path)
    secret_text = ("user https://alice:secretpass@example.test --token abcsecret\n"
                   "мама купи хлеб\n")
    run = _Run(outputs={"uname": secret_text, "journalctl": secret_text})

    snap = take_snapshot(cfg, "boot-redact", run=run, now=lambda: 14)

    for name in ("uname.txt", "prev_journal_tail.txt"):
        text = _read(snap, name)
        assert "secretpass" not in text and "abcsecret" not in text
        assert "<скрыто>" in text
    assert "мама купи хлеб" not in _read(snap, "prev_journal_tail.txt")
