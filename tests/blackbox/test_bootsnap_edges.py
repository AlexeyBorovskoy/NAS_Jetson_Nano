"""OBS-1, задача 8: краевые случаи bootsnap — защита пути, частичный отказ, маскирование.

Синтетика: корни — tmp_path, `run` и `now` подменяются, настоящие процессы и
файлы хоста не трогаются (как tests/blackbox/test_bootsnap.py).
"""
import os
import subprocess

import pytest

from blackbox import bootsnap
from blackbox.bootsnap import take_snapshot
from blackbox.config import Config

MOUNTS = "/dev/sda1 /mnt/storage ext4 rw,noatime 0 0\n"


def _cfg(tmp_path, ssd_root=None):
    """Config с подставными корнями; ssd_mount — корень диска (ismount истинно)."""
    proc = tmp_path / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "mounts").write_text(MOUNTS, encoding="utf-8")
    (tmp_path / "sys" / "fs" / "pstore").mkdir(parents=True, exist_ok=True)
    return Config(ssd_root=str(ssd_root or (tmp_path / "ssd" / "blackbox")),
                  fallback_root=str(tmp_path / "fallback"),
                  ssd_mount=tmp_path.anchor,
                  sysfs_root=str(tmp_path / "sys"),
                  proc_root=str(proc),
                  dev_root=str(tmp_path / "dev"))


class _Done(object):
    """Ответ как у subprocess.CompletedProcess в текстовом режиме."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _Run(object):
    """Подставной subprocess.run: вывод по ключу, выбранные команды падают."""

    def __init__(self, outputs=None, failing=(), timeout=False):
        self.outputs = outputs or {}
        self.failing = tuple(failing)
        self.timeout = timeout
        self.calls = []

    def __call__(self, args, **kwargs):
        cmd = " ".join(str(a) for a in args)
        self.calls.append(cmd)
        if self.timeout:
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        for key in self.failing:
            if key in cmd:
                return _Done(returncode=1)
        for key, out in self.outputs.items():
            if key in cmd:
                return _Done(stdout=out)
        return _Done()


def _read(snap, name):
    with open(os.path.join(str(snap), name), "r", encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("bad", ["..", "../x", "a/b", "a\\b", ".", "", None,
                                 "C:relative", "bad\nname", "x" * 129])
def test_bad_boot_id_rejected_before_any_write(tmp_path, bad):
    """Путь за пределы `boots/` не строится: ValueError до создания каталогов."""
    cfg = _cfg(tmp_path)
    with pytest.raises(ValueError):
        take_snapshot(cfg, bad, run=_Run(), now=lambda: 1)
    assert not os.path.exists(str(cfg.fallback_root))
    assert not os.path.exists(str(cfg.ssd_root))


def test_partial_failure_keeps_snapshot_with_fixed_error(tmp_path):
    """Упавшая команда без stderr -> фиксированный класс/код; снимок создан целиком."""
    cfg = _cfg(tmp_path)
    run = _Run(outputs={"uname": "Linux jetson\n"}, failing=("dmesg",))

    snap = take_snapshot(cfg, "boot-1", run=run, now=lambda: 7)

    assert _read(snap, "uname.txt") == "Linux jetson\n"
    assert _read(snap, "dmesg.txt") == "dmesg: " + bootsnap.ERROR_UNAVAILABLE
    assert _read(snap, "reset_source.txt").startswith(bootsnap.ERROR_RESET)
    assert os.path.isfile(os.path.join(str(snap), "summary.json"))
    assert os.path.isdir(os.path.join(str(snap), "pstore"))


def test_command_timeout_is_fixed_error(tmp_path):
    """Таймаут команды -> фиксированный класс ошибки, снимок создан."""
    cfg = _cfg(tmp_path)
    snap = take_snapshot(cfg, "boot-2", run=_Run(timeout=True), now=lambda: 8)
    assert bootsnap.ERROR_TIMEOUT in _read(snap, "uname.txt")
    assert os.path.isfile(os.path.join(str(snap), "summary.json"))


def test_ssd_write_failure_falls_back(tmp_path):
    """SSD смонтирован, но каталог создать нельзя -> снимок в запасном корне."""
    blocked = tmp_path / "blocked"
    blocked.write_text("не каталог", encoding="utf-8")
    cfg = _cfg(tmp_path, ssd_root=str(blocked / "blackbox"))

    snap = take_snapshot(cfg, "boot-3", run=_Run(), now=lambda: 9)

    assert os.path.normpath(str(snap)).startswith(
        os.path.normpath(str(cfg.fallback_root)))
    assert os.path.isfile(os.path.join(str(snap), "summary.json"))
    assert not os.path.exists(str(blocked / "blackbox"))


def test_text_outputs_are_redacted(tmp_path):
    """Секреты в текстовых выводах маскируются redact_line перед записью."""
    cfg = _cfg(tmp_path)
    (tmp_path / "proc" / "mounts").write_text("password=hunter2 x\n",
                                              encoding="utf-8")
    run = _Run(outputs={
        "uname": "token=abc123secret release\n",
        "dmesg": "PMC reset source: TEGRA_POWER_ON_RESET token=zzz999\n",
    })

    snap = take_snapshot(cfg, "boot-4", run=run, now=lambda: 10)

    assert "abc123secret" not in _read(snap, "uname.txt")
    assert "<скрыто>" in _read(snap, "uname.txt")
    assert "hunter2" not in _read(snap, "mounts.txt")
    reset = _read(snap, "reset_source.txt")
    assert "zzz999" not in reset
    assert "PMC reset source" in reset


def test_pstore_file_over_limit_is_truncated_with_marker(tmp_path, monkeypatch):
    """Файл pstore больше предела -> первые PSTORE_MAX_BYTES и явная пометка."""
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(bootsnap, "PSTORE_MAX_BYTES", 16)
    name = "dmesg-ramoops-0"
    with open(os.path.join(cfg.sysfs_root, "fs", "pstore", name), "wb") as fh:
        fh.write(b"A" * 40)

    snap = take_snapshot(cfg, "boot-5", run=_Run(), now=lambda: 11)

    with open(os.path.join(str(snap), "pstore", name), "rb") as fh:
        assert fh.read() == b"A" * 16
    marker = os.path.join(str(snap), "pstore", name + ".truncated")
    with open(marker, "r", encoding="utf-8") as fh:
        assert "truncated: 16 of 40 bytes" in fh.read()
    assert name in _read(snap, "summary.json")


def test_missing_mounts_file_gives_fixed_error(tmp_path):
    """Нет `<proc_root>/mounts` -> файл с фиксированным классом, без исключения."""
    cfg = _cfg(tmp_path)
    os.remove(os.path.join(cfg.proc_root, "mounts"))

    snap = take_snapshot(cfg, "boot-6", run=_Run(), now=lambda: 12)

    assert _read(snap, "mounts.txt").startswith(bootsnap.ERROR_READ)
