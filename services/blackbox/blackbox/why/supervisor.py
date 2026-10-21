"""Deadline-bound parent for the evidence worker."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from blackbox.config import load_config
from blackbox.archive_supervisor import _proc_starttime, _signal_worker, _wait_until_exit

TIMEOUT_S = 50
GRACE_S = 2
OUTPUT_MAX = 65536
MARKER = "why-worker.json"


def _marker_path(cfg):
    return os.path.join(_state_dir(cfg), MARKER)


def _state_dir(cfg):
    root = cfg.fallback_root
    if os.path.islink(root):
        raise OSError("unsafe fallback state root")
    state = os.path.join(root, "why-state")
    if os.path.islink(state):
        raise OSError("unsafe fallback state directory")
    if not os.path.isdir(state):
        os.makedirs(state, mode=0o700)
    return state


def _read_marker(path):
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = json.loads(stream.read(1025))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _active(path, proc_root):
    value = _read_marker(path)
    if not value or not isinstance(value.get("pid"), int):
        return False
    actual = _proc_starttime(proc_root, value["pid"])
    if value.get("starttime") is None:
        return os.path.isdir(os.path.join(proc_root, str(value["pid"])))
    return actual == value.get("starttime")


def _clear_stale_marker(path, proc_root):
    try:
        before = os.lstat(path)
        if os.path.islink(path) or not os.path.isfile(path) or _active(path, proc_root):
            return False
        after = os.lstat(path)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            return False
        os.unlink(path)
        return True
    except OSError:
        return False


def _claim(cfg, proc_root):
    try:
        path = _marker_path(cfg)
    except OSError:
        return None, "fallback state unavailable"
    if _active(path, proc_root):
        return None, "worker already active"
    try:
        if os.path.lexists(path):
            if not _clear_stale_marker(path, proc_root):
                return None, "worker marker busy or unsafe"
        parent_start = _proc_starttime(proc_root, os.getpid())
        if not parent_start:
            return None, "process identity unavailable"
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "starttime": parent_start}, stream)
    except OSError:
        return None, "worker marker busy"
    return path, None


def _remove(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _remove_owned(path, expected):
    try:
        before = os.lstat(path)
        value = _read_marker(path)
        after = os.lstat(path)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            return False
        if value and value.get("pid") == expected.get("pid") and value.get(
                "starttime") == expected.get("starttime"):
            os.unlink(path)
            return True
    except OSError:
        return False
    return False


def _worker_command(script, marker, args):
    return [sys.executable, script, "--worker", marker] + list(args)


def _start(cfg, entrypoint, args, marker, popen, proc_root):
    try:
        state = _state_dir(cfg)
        if shutil.disk_usage(state).free < OUTPUT_MAX + 4096:
            return None, None, "fallback output space unavailable", False
        fd, out_path = tempfile.mkstemp(prefix="why-output-", dir=state)
        stream = os.fdopen(fd, "wb")
    except OSError:
        return None, None, "fallback output unavailable", False
    try:
        proc = popen(_worker_command(entrypoint, marker, args), stdout=stream,
                     stderr=subprocess.DEVNULL, close_fds=True,
                     start_new_session=(os.name == "posix"))
    except (OSError, ValueError):
        stream.close()
        _remove(out_path)
        return None, None, "worker start failed", False
    stream.close()
    try:
        start = _proc_starttime(proc_root, proc.pid)
        if not start:
            _write_marker(marker, {"pid": int(proc.pid), "starttime": None})
            raise ValueError("worker identity unavailable")
        _write_marker(marker, {"pid": int(proc.pid), "starttime": start})
    except (OSError, ValueError):
        _signal_worker(proc, signal.SIGTERM)
        _signal_worker(proc, getattr(signal, "SIGKILL", 9))
        alive = proc.poll() is None
        if alive:
            _write_marker(marker, {"pid": int(proc.pid), "starttime": None})
        _remove(out_path)
        return None, None, "worker identity unavailable", alive
    return proc, out_path, None, False


def _write_marker(path, value):
    fd, temp = tempfile.mkstemp(prefix="why-marker-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except OSError:
        _remove(temp)
        raise


def _stop(proc, clock, sleep):
    _signal_worker(proc, signal.SIGTERM)
    _wait_until_exit(proc, clock() + GRACE_S, clock, sleep)
    if proc.poll() is None:
        _signal_worker(proc, getattr(signal, "SIGKILL", 9))


def _read_output(path, writer):
    try:
        with open(path, "rb") as stream:
            data = stream.read(OUTPUT_MAX + 1)
        writer(data[:OUTPUT_MAX].decode("utf-8", "replace"))
    except OSError:
        writer("unknown: worker output unavailable\n")


def supervise(cfg, entrypoint, args, popen=subprocess.Popen,
              clock=time.monotonic, sleep=time.sleep, writer=None, timeout=TIMEOUT_S):
    writer = writer or sys.stdout.write
    timeout = min(TIMEOUT_S, max(0.0, timeout))
    marker, error = _claim(cfg, cfg.proc_root)
    if error:
        writer("unknown: %s\n" % error)
        return 0
    output = None
    keep_marker = False
    marker_owner = _read_marker(marker)
    try:
        proc, output, error, keep_marker = _start(cfg, entrypoint, args, marker, popen, cfg.proc_root)
        if error:
            writer("unknown: %s\n" % error)
            return 0
        code = _wait_until_exit(proc, clock() + timeout, clock, sleep)
        if code is None:
            _stop(proc, clock, sleep)
            keep_marker = proc.poll() is None
            writer("unknown: evidence deadline exceeded\n")
            return 0
        if code != 0:
            writer("unknown: evidence worker failed\n")
            return 0
        _read_output(output, writer)
        return 0
    finally:
        if output:
            _remove(output)
        if not keep_marker:
            current = _read_marker(marker)
            if current and current.get("pid") != marker_owner.get("pid"):
                marker_owner = current
            _remove_owned(marker, marker_owner)


def worker_authorized(marker, proc_root, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + 5
    while clock() < deadline:
        value = _read_marker(marker)
        if value and value.get("pid") == os.getpid():
            return _proc_starttime(proc_root, os.getpid()) == value.get("starttime")
        sleep(min(0.1, max(0.0, deadline - clock())))
    return False


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    cfg = load_config()
    if args and args[0] == "--worker":
        marker = args[1] if len(args) > 1 else ""
        if not worker_authorized(marker, cfg.proc_root):
            print("unknown: worker not authorized")
            return 0
        from blackbox.why.worker_limits import apply_memory_limit
        if not apply_memory_limit():
            print("unknown: worker memory limit unavailable")
            return 2
        from blackbox.why.cli import main as cli_main
        return cli_main(args[2:], cfg=cfg, supervised=True)
    script = os.path.abspath(sys.argv[0])
    return supervise(cfg, script, args)
