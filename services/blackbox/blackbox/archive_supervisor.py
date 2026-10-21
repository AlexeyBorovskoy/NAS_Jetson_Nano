"""SSD/proc-only parent supervisor for the HDD archive worker."""
import json
import os
import signal
import subprocess
import sys
import time

from .config import load_config

WORKER_TIMEOUT_S = 3600
TERM_GRACE_S = 3
KILL_SIGNAL = getattr(signal, "SIGKILL", 9)
MARKER_NAME = "blackbox-archive-worker.json"
MARKER_LIMIT = 1024


def worker_marker_path(cfg):
    return os.path.join(cfg.ssd_root, "staging", MARKER_NAME)


def _proc_starttime(proc_root, pid):
    """Returns Linux process starttime (field 22), excluding exited zombies."""
    path = os.path.join(proc_root, str(pid), "stat")
    try:
        with open(path, "r", encoding="ascii") as fh:
            text = fh.read(4096)
    except (OSError, UnicodeError):
        return None
    end = text.rfind(")")
    fields = text[end + 2:].split() if end >= 0 else []
    if len(fields) < 20 or fields[0] == "Z":
        return None
    return fields[19]


def _read_marker(path):
    """Reads a small regular marker without following symlinks."""
    try:
        if os.path.islink(path) or not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = fh.read(MARKER_LIMIT + 1)
        if len(data) > MARKER_LIMIT:
            return None
        value = json.loads(data)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get("pid"), int):
        return None
    if not isinstance(value.get("starttime"), str):
        return None
    return value


def _active_marker(marker, proc_root):
    value = _read_marker(marker)
    if value is None:
        return None
    actual = _proc_starttime(proc_root, value["pid"])
    return value if actual == value["starttime"] else None


def _write_exclusive(path, value):
    """Creates reservation marker atomically with private permissions."""
    data = json.dumps(value, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())


def _replace_marker(path, value):
    temp = path + ".tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(json.dumps(value, sort_keys=True).encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, path)


def _remove_marker(path, expected):
    value = _read_marker(path)
    if value and value.get("pid") == expected["pid"] and value.get(
            "starttime") == expected["starttime"]:
        try:
            os.unlink(path)
        except OSError:
            return False
        return True
    return False


def _ssd_available(cfg):
    """Confirms the configured state directory is under the live SSD mount."""
    if not os.path.ismount(cfg.ssd_mount):
        return False
    return _ssd_path_safe(cfg.ssd_mount, cfg.ssd_root)


def _ssd_path_safe(mount, path):
    """Checks an SSD path below its mount without following symbolic links."""
    try:
        mount = os.path.normcase(os.path.abspath(mount))
        target = os.path.normcase(os.path.abspath(path))
        if os.path.commonpath((mount, target)) != mount:
            return False
        current = mount
        for part in os.path.relpath(target, mount).split(os.sep):
            if part in ("", "."):
                continue
            current = os.path.join(current, part)
            if os.path.islink(current):
                return False
        return True
    except (OSError, ValueError):
        return False


def _clear_stale_marker(path, proc_root):
    """Removes a stale regular marker only if its inode has not changed."""
    try:
        before = os.lstat(path)
    except OSError:
        return True
    if os.path.islink(path) or not os.path.isfile(path):
        return False
    if _active_marker(path, proc_root) is not None:
        return False
    try:
        after = os.lstat(path)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            return False
        os.unlink(path)
    except OSError:
        return False
    return True


def _signal_worker(proc, sig):
    """Sends a signal without waiting for child reaping."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, sig)
        elif sig == signal.SIGTERM:
            proc.terminate()
        else:
            proc.kill()
    except OSError:
        return False
    return True


def _wait_until_exit(proc, deadline, clock, sleep):
    while clock() < deadline:
        code = proc.poll()
        if code is not None:
            return code
        sleep(min(0.2, max(0.0, deadline - clock())))
    return proc.poll()


def _terminate(proc, clock, sleep):
    _signal_worker(proc, signal.SIGTERM)
    code = _wait_until_exit(proc, clock() + TERM_GRACE_S, clock, sleep)
    if code is None:
        _signal_worker(proc, KILL_SIGNAL)
        code = proc.poll()
    return code


def _reserve_worker(cfg):
    """Claims the SSD marker before spawning, preventing concurrent supervisors."""
    if not _ssd_available(cfg):
        return None, None, {"status": "deferred", "reason": "ssd unavailable"}
    staging = os.path.join(cfg.ssd_root, "staging")
    if not _prepare_staging(cfg, staging):
        return None, None, {"status": "failed", "reason": "unsafe ssd root"}
    try:
        marker = worker_marker_path(cfg)
        proc_root = cfg.proc_root
        if os.path.lexists(marker):
            if _active_marker(marker, proc_root) is not None:
                return None, None, {"status": "deferred", "reason": "worker active"}
            if not _clear_stale_marker(marker, proc_root):
                return None, None, {"status": "deferred", "reason": "worker marker busy"}
        parent_marker = {"pid": os.getpid(),
                         "starttime": _proc_starttime(proc_root, os.getpid())}
        if not parent_marker["starttime"]:
            return None, None, {"status": "failed", "reason": "proc identity unavailable"}
        _write_exclusive(marker, parent_marker)
    except FileExistsError:
        return None, None, {"status": "deferred", "reason": "worker starting"}
    except OSError:
        return None, None, {"status": "failed", "reason": "supervisor setup failed"}
    return marker, parent_marker, None


def _prepare_staging(cfg, staging):
    if os.path.islink(cfg.ssd_root) or os.path.islink(staging):
        return False
    if not _ssd_path_safe(cfg.ssd_mount, staging):
        return False
    if not os.path.isdir(staging):
        try:
            os.makedirs(staging, mode=0o700)
        except OSError:
            return False
    return True


def _start_worker(marker, parent_marker, proc_root, entrypoint, popen):
    """Spawns one session and replaces the reservation with worker identity."""
    proc = None
    try:
        proc = popen([sys.executable, entrypoint, "--worker"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=(os.name == "posix"), close_fds=True)
        worker_marker = {"pid": int(proc.pid),
                         "starttime": _proc_starttime(proc_root, proc.pid)}
        if not worker_marker["starttime"]:
            _signal_worker(proc, signal.SIGTERM)
            _signal_worker(proc, KILL_SIGNAL)
            _remove_marker(marker, parent_marker)
            return None, None
        _replace_marker(marker, worker_marker)
    except (OSError, ValueError):
        if proc is not None:
            _signal_worker(proc, signal.SIGTERM)
            _signal_worker(proc, KILL_SIGNAL)
        _remove_marker(marker, parent_marker)
        return None, None
    return proc, worker_marker


def _monitor_worker(proc, marker, identity, clock, sleep, timeout):
    code = _wait_until_exit(proc, clock() + timeout, clock, sleep)
    if code is not None:
        _remove_marker(marker, identity)
        status = "completed" if code == 0 else "failed"
        reason = "worker exited" if code == 0 else "worker failed"
        return {"status": status, "reason": reason}
    code = _terminate(proc, clock, sleep)
    if code is not None:
        _remove_marker(marker, identity)
    return {"status": "deferred", "reason": "worker deadline exceeded"}


def supervise(cfg, entrypoint, popen=subprocess.Popen, clock=time.monotonic,
              sleep=time.sleep, timeout=WORKER_TIMEOUT_S):
    """Starts at most one marked worker; only polls and never blocks to reap it."""
    marker, parent_marker, error = _reserve_worker(cfg)
    if error:
        return error
    proc, worker_marker = _start_worker(marker, parent_marker, cfg.proc_root,
                                        entrypoint, popen)
    if proc is None:
        return {"status": "failed", "reason": "worker start failed"}
    return _monitor_worker(proc, marker, worker_marker, clock, sleep, timeout)


def await_worker_authorization(marker, proc_root, timeout=20,
                               clock=time.monotonic, sleep=time.sleep):
    """Worker waits until the parent publishes its PID/starttime marker."""
    pid = os.getpid()
    start = _proc_starttime(proc_root, pid)
    if not start:
        return False
    deadline = clock() + timeout
    while clock() < deadline:
        value = _read_marker(marker)
        if value and value.get("pid") == pid and value.get("starttime") == start:
            return True
        sleep(min(0.1, max(0.0, deadline - clock())))
    return False


def main(argv=None):
    cfg = load_config()
    script = os.path.abspath(sys.argv[0])
    result = supervise(cfg, script)
    return 0 if result["status"] in ("completed", "deferred") else 1
