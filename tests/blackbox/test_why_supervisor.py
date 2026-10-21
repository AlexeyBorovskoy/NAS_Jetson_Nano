"""Process supervision tests use only synthetic proc files and temporary SSD roots."""
import os
import signal

from blackbox.config import Config
from blackbox.why.supervisor import supervise


def _stat(root, pid, start="12345"):
    path = root / str(pid)
    path.mkdir(exist_ok=True)
    fields = ["S"] + ["0"] * 18 + [start]
    (path / "stat").write_text("%d (fake) %s\n" % (pid, " ".join(fields)), encoding="ascii")


class Clock(object):
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, duration):
        self.value += duration


class Proc(object):
    pid = 4321

    def __init__(self, code, output=None):
        self.code = code
        self.output = output
        self.signals = []

    def poll(self):
        return self.code


def _fixture(tmp_path, monkeypatch):
    ssd = tmp_path / "ssd"
    proc_root = tmp_path / "proc"
    ssd.mkdir()
    fallback = tmp_path / "fallback"
    fallback.mkdir()
    proc_root.mkdir()
    _stat(proc_root, os.getpid())
    _stat(proc_root, 4321)
    monkeypatch.setattr(os.path, "ismount", lambda path: True)
    cfg = Config(ssd_root=str(ssd), fallback_root=str(fallback),
                 ssd_mount=str(ssd), proc_root=str(proc_root))
    return cfg, proc_root


def test_success_forwards_bounded_private_worker_output(tmp_path, monkeypatch):
    cfg, proc_root = _fixture(tmp_path, monkeypatch)
    clock, output = Clock(), []
    proc = Proc(0)

    def popen(argv, **kwargs):
        kwargs["stdout"].write(b"verdict: synthetic\n")
        return proc

    status = supervise(cfg, "nas-why", ["--boot", "-1", "--short"],
                       popen=popen, clock=clock, sleep=clock.sleep,
                       writer=output.append)
    assert status == 0 and output == ["verdict: synthetic\n"]
    assert os.listdir(os.path.join(cfg.fallback_root, "why-state")) == []


def test_timeout_kills_without_blocking_wait_and_returns_unknown(tmp_path, monkeypatch):
    cfg, proc_root = _fixture(tmp_path, monkeypatch)
    clock, output = Clock(), []

    class Hanging(Proc):
        def poll(self):
            return None

    process = Hanging(None)

    def popen(argv, **kwargs):
        return process

    from blackbox.why import supervisor
    signals = []
    monkeypatch.setattr(supervisor, "_signal_worker", lambda proc, sig: signals.append(sig))
    result = supervise(cfg, "nas-why", [], popen=popen, clock=clock,
                       sleep=clock.sleep, writer=output.append, timeout=0.5)
    assert result == 0 and output == ["unknown: evidence deadline exceeded\n"]
    assert signal.SIGTERM in signals and getattr(signal, "SIGKILL", 9) in signals
    marker = os.path.join(cfg.fallback_root, "why-state", "why-worker.json")
    assert os.path.isfile(marker)

    def duplicate(*args, **kwargs):
        raise AssertionError("duplicate worker")

    second = supervise(cfg, "nas-why", [], popen=duplicate, clock=clock,
                       sleep=clock.sleep, writer=output.append)
    assert second == 0 and "worker already active" in output[-1]
    assert os.path.isfile(marker)


def test_worker_failure_never_forwards_partial_output(tmp_path, monkeypatch):
    cfg, _proc_root = _fixture(tmp_path, monkeypatch)
    output = []

    def popen(argv, **kwargs):
        kwargs["stdout"].write(b"partial healthy-looking output")
        return Proc(2)

    assert supervise(cfg, "nas-why", [], popen=popen, writer=output.append) == 0
    assert output == ["unknown: evidence worker failed\n"]


def test_parent_uses_fallback_state_when_ssd_is_unmounted(tmp_path, monkeypatch):
    cfg, _proc_root = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(os.path, "ismount", lambda path: False)
    output = []

    def popen(argv, **kwargs):
        kwargs["stdout"].write(b"fallback evidence\n")
        return Proc(0)

    supervise(cfg, "nas-why", [], popen=popen, writer=output.append)
    assert output == ["fallback evidence\n"]
    assert os.path.isdir(os.path.join(cfg.fallback_root, "why-state"))
