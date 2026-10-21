"""Persist boot transitions and snapshot associations in the active catalog."""
import json
import math
import os
import re
import stat
import time

from . import bootsnap
from .store import Catalog, read_heartbeat

BOOT_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SUMMARY_LIMIT = 64 * 1024
RESET_LIMIT = 4 * 1024
JOURNAL_LIMIT = 4 * 1024 * 1024
HEARTBEAT_LIMIT = 64 * 1024
PROC_LIMIT = 4096


def _safe_path(path):
    """Reject paths with symlink components, without resolving through them."""
    absolute = os.path.abspath(path)
    current = os.path.splitdrive(absolute)[0] + os.sep
    for part in absolute[len(current):].split(os.sep):
        if not part:
            continue
        current = os.path.join(current, part)
        if os.path.islink(current):
            return False
    return True


def _read_bounded(path, limit):
    """Read one regular file with no symlink following and a strict byte cap."""
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise OSError("boot record: unsafe or oversized input")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as fh:
        opened = os.fstat(fh.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("boot record: input changed")
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise OSError("boot record: oversized input")
    return data.decode("utf-8", "replace")


def _snapshot_root(cfg, boot_id, snapshot_dir):
    bootsnap._check_boot_id(boot_id)
    target = os.path.normcase(os.path.abspath(snapshot_dir))
    choices = ((cfg.ssd_root, os.path.join(cfg.ssd_root, "boots", boot_id),
                os.path.ismount(cfg.ssd_mount)),
               (cfg.fallback_root,
                os.path.join(cfg.fallback_root, "boots", boot_id), True))
    for root, expected, enabled in choices:
        expected = os.path.normcase(os.path.abspath(expected))
        if enabled and target == expected and _safe_path(root) and _safe_path(target):
            return root
    raise OSError("boot record: snapshot path rejected")


def _snapshot_data(snapshot_dir, boot_id, now):
    summary = json.loads(_read_bounded(
        os.path.join(snapshot_dir, "summary.json"), SUMMARY_LIMIT))
    if (not isinstance(summary, dict) or summary.get("boot_id") != boot_id or
            not _valid_ts(summary.get("ts")) or summary["ts"] > now):
        raise ValueError("boot record: invalid snapshot summary")
    journal = _read_bounded(
        os.path.join(snapshot_dir, "prev_journal_tail.txt"), JOURNAL_LIMIT)
    reset = _read_bounded(
        os.path.join(snapshot_dir, "reset_source.txt"), RESET_LIMIT)
    pstore = summary.get("pstore")
    if not isinstance(pstore, list):
        pstore = []
    pstore = [name for name in pstore if isinstance(name, str) and
              name and os.path.basename(name) == name and name not in (".", "..")]
    return int(summary["ts"]), journal.splitlines(), reset[:RESET_LIMIT], pstore


def _valid_ts(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(value) and value >= 0)


def _heartbeat(path, now):
    if not _safe_path(path):
        return None
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > HEARTBEAT_LIMIT:
            return None
        value = read_heartbeat(path)
    except OSError:
        return None
    if not isinstance(value, dict) or not _valid_ts(value.get("ts")):
        return None
    if value["ts"] > now or not isinstance(value.get("boot_id"), str):
        return None
    if not BOOT_RE.match(value["boot_id"]):
        return None
    return value


def _heartbeats(cfg, now):
    paths = [os.path.join(cfg.fallback_root, "heartbeat")]
    if os.path.ismount(cfg.ssd_mount):
        paths.append(os.path.join(cfg.ssd_root, "heartbeat"))
    return [value for value in (_heartbeat(path, now) for path in paths)
            if value is not None]


def _previous_heartbeat(heartbeats, current_id):
    candidates = [hb for hb in heartbeats if hb["boot_id"] != current_id]
    return max(candidates, key=lambda hb: hb["ts"]) if candidates else None


def _boot_start(proc_root, now, fallback):
    """Read configured proc btime; fallback snapshot time is approximate."""
    try:
        text = _read_bounded(os.path.join(proc_root, "stat"), PROC_LIMIT)
    except OSError:
        return fallback
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] == "btime" and fields[1].isdigit():
            value = int(fields[1])
            if 0 < value <= now:
                return value
    return fallback


def _current_row(catalog, boot_id, start):
    existing = catalog.get_boot(boot_id) or {}
    return {"boot_id": boot_id, "start": existing.get("start") or start,
            "end": None, "clean": None, "last_heartbeat": None,
            "reset_source": None, "pstore": [],
            "verdict": existing.get("verdict"),
            "confidence": existing.get("confidence")}


def _heartbeat_evidence(heartbeat):
    """Preserve the last measured power without copying arbitrary heartbeat fields."""
    source = heartbeat.get("power")
    source = source if isinstance(source, dict) else {}
    power = {}
    for key in ("vin_mv", "vin_ma", "cpu_mw", "gpu_mw"):
        value = source.get(key)
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        power[key] = value if valid and math.isfinite(value) else None
    return {"boot_id": heartbeat["boot_id"], "ts": heartbeat["ts"], "power": power}


def record_boot(cfg, current_boot_id, snapshot_dir, now):
    """Record previous boot evidence once per transition and upsert current boot."""
    if not isinstance(current_boot_id, str) or not BOOT_RE.match(current_boot_id):
        raise ValueError("boot record: invalid boot id")
    if not _valid_ts(now):
        raise ValueError("boot record: invalid time")
    now = float(now)
    active_root = _snapshot_root(cfg, current_boot_id, snapshot_dir)
    summary_ts, journal, reset, pstore = _snapshot_data(
        snapshot_dir, current_boot_id, now)
    catalog_path = os.path.join(active_root, "catalog.db")
    if not _safe_path(catalog_path) or os.path.islink(catalog_path):
        raise OSError("boot record: catalog path rejected")
    catalog = Catalog(catalog_path)
    try:
        heartbeats = _heartbeats(cfg, now)
        retry = (catalog.get_cursor("active_boot") == current_boot_id or
                 any(hb["boot_id"] == current_boot_id for hb in heartbeats))
        previous = _previous_heartbeat(heartbeats, current_boot_id)
        if not retry and previous is not None:
            row = bootsnap.previous_boot_summary(
                catalog, previous, journal, pstore, reset)
            catalog.upsert_boot(row)
            catalog.set_cursor("boot-snapshot:" + previous["boot_id"],
                               current_boot_id)
            catalog.set_cursor("boot-heartbeat:" + previous["boot_id"],
                               json.dumps(_heartbeat_evidence(previous), sort_keys=True))
        start = _boot_start(cfg.proc_root, now, summary_ts)
        catalog.upsert_boot(_current_row(catalog, current_boot_id, start))
        catalog.set_cursor("active_boot", current_boot_id)
    finally:
        catalog.close()
