"""Supervisor lifecycle tests with synthetic proc identities and no child processes."""
import json
import os
import signal

from blackbox import archive_supervisor as supervisor
from blackbox.config import Config


class _Clock(object):
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, amount):
        self.now += amount


class _Process(object):
    pid = 456

    def __init__(self, code=0):
        self.code = code
        self.signals = []

    def poll(self):
        return self.code


def _cfg(tmp_path):
    root = tmp_path / "ssd"
    (root / "staging").mkdir(parents=True)
    return Config(ssd_root=str(root), ssd_mount=str(tmp_path),
                  proc_root=str(tmp_path / "proc"))


def _marker(cfg, pid, start):
    path = supervisor.worker_marker_path(cfg)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pid": pid, "starttime": start}, fh)
    return path


def test_live_worker_marker_defers_without_spawning(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    marker = _marker(cfg, 123, "same-start")
    monkeypatch.setattr(supervisor, "_ssd_available", lambda _cfg: True)
    monkeypatch.setattr(supervisor, "_proc_starttime",
                        lambda _root, pid: "same-start" if pid == 123 else "parent")
    result = supervisor.supervise(cfg, "archive.py",
                                  popen=lambda *_a, **_k: (_ for _ in ()).throw(
                                      AssertionError("second worker")))
    assert result["status"] == "deferred"
    assert os.path.isfile(marker)


def test_pid_reuse_stale_marker_allows_new_worker(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    marker = _marker(cfg, 123, "old-start")
    process = _Process(0)
    identities = {123: "new-start", os.getpid(): "parent-start", 456: "child-start"}
    monkeypatch.setattr(supervisor, "_ssd_available", lambda _cfg: True)
    monkeypatch.setattr(supervisor, "_proc_starttime",
                        lambda _root, pid: identities.get(pid))
    calls = []

    def popen(args, **kwargs):
        calls.append((args, kwargs))
        return process

    result = supervisor.supervise(cfg, "archive.py", popen=popen,
                                  clock=lambda: 0, sleep=lambda _s: None)
    assert result["status"] == "completed"
    assert len(calls) == 1 and calls[0][0][-1] == "--worker"
    assert not os.path.exists(marker)


def test_deadline_signals_without_wait_and_keeps_live_marker(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    process = _Process(None)
    clock = _Clock()
    identities = {os.getpid(): "parent-start", 456: "child-start"}
    monkeypatch.setattr(supervisor, "_ssd_available", lambda _cfg: True)
    monkeypatch.setattr(supervisor, "_proc_starttime",
                        lambda _root, pid: identities.get(pid))
    monkeypatch.setattr(supervisor, "_signal_worker",
                        lambda proc, sig: proc.signals.append(sig) or True)
    result = supervisor.supervise(cfg, "archive.py", popen=lambda *_a, **_k: process,
                                  clock=clock.time, sleep=clock.sleep, timeout=0)
    assert result["status"] == "deferred"
    assert process.signals == [signal.SIGTERM, supervisor.KILL_SIGNAL]
    assert os.path.isfile(supervisor.worker_marker_path(cfg))
    assert not hasattr(process, "wait")
