"""Weekly OBS-1 archive building and verified HDD transport (task 9)."""
import datetime
import hashlib
import lzma
import os
import re
import shutil
import stat
import sqlite3
import subprocess
import tarfile
import tempfile
import time

from .config import load_config
from .store import Catalog

WEEK_RE = re.compile(r"^(\d{4})-W(0[1-9]|[1-4][0-9]|5[0-3])$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARCHIVE_RE = re.compile(r"^blackbox-(\d{4}-W\d{2})\.tar\.xz$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMAND_TIMEOUT = 30
SHIP_TIMEOUT = 1800
VERIFY_TIMEOUT = 600
FIXED_ERROR = "archive operation failed"


def _parse_day(value):
    """Строго проверяет дату YYYY-MM-DD."""
    if not isinstance(value, str) or not DAY_RE.match(value):
        raise ValueError("archive: invalid day")
    parsed = datetime.datetime.strptime(value, "%Y-%m-%d").date()
    if parsed.isoformat() != value:
        raise ValueError("archive: invalid day")
    return parsed


def _week_bounds(week):
    """ISO week -> Monday/Sunday; rejects non-calendar week 53."""
    match = WEEK_RE.match(week) if isinstance(week, str) else None
    if not match:
        raise ValueError("archive: invalid week")
    year, number = int(match.group(1)), int(match.group(2))
    jan4 = datetime.date(year, 1, 4)
    monday = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
    monday += datetime.timedelta(weeks=number - 1)
    iso = monday.isocalendar()
    if iso[0] != year or iso[1] != number:
        raise ValueError("archive: invalid week")
    return monday, monday + datetime.timedelta(days=6)


def _today_date(today):
    return _parse_day(today)


def _day_directories(hot_root):
    """Returns valid, non-symlink day directories in ascending order."""
    if not os.path.isdir(hot_root) or os.path.islink(hot_root):
        return []
    found = []
    for name in sorted(os.listdir(hot_root)):
        if not DAY_RE.match(name):
            continue
        path = os.path.join(hot_root, name)
        if os.path.islink(path) or not os.path.isdir(path):
            continue
        try:
            _parse_day(name)
        except ValueError:
            continue
        found.append(name)
    return found


def weeks_due(hot_root, today, min_age_days=7):
    """Returns complete ISO weeks whose Sunday is older than the age cutoff."""
    current = _today_date(today)
    if not isinstance(min_age_days, int) or min_age_days < 0:
        raise ValueError("archive: invalid minimum age")
    cutoff = current - datetime.timedelta(days=min_age_days)
    weeks = set()
    for name in _day_directories(hot_root):
        day = _parse_day(name)
        iso = day.isocalendar()
        week = "%04d-W%02d" % (iso[0], iso[1])
        _monday, sunday = _week_bounds(week)
        if sunday < current and sunday <= cutoff:
            weeks.add(week)
    return sorted(weeks)


def _run(run, argv, timeout):
    """Executes a bounded argv command and hides all command error output."""
    try:
        return run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                   universal_newlines=True, timeout=timeout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def hdd_busy(cfg, run=subprocess.run):
    """Returns active work, None when idle, or busycheck_failed when unknown."""
    for unit in cfg.hdd_busy_units:
        result = _run(run, ("systemctl", "is-active", "--quiet", unit),
                      COMMAND_TIMEOUT)
        if result is None or result.returncode not in (0, 3):
            return "busycheck_failed"
        if result.returncode == 0:
            return unit
    result = _run(run, ("pgrep", "-x", "restic"), COMMAND_TIMEOUT)
    if result is None or result.returncode not in (0, 1):
        return "busycheck_failed"
    return "restic" if result.returncode == 0 else None


def hdd_alive(cfg, run=subprocess.run):
    """Checks mount responsiveness with a bounded stat command."""
    result = _run(run, ("timeout", "5", "stat", "-f", cfg.hdd_mount), 8)
    return result is not None and result.returncode == 0


def _week_days(hot_root, week):
    """Existing safe day directories for one ISO week, oldest first."""
    monday, sunday = _week_bounds(week)
    today = datetime.datetime.utcnow().date()
    if sunday >= today:
        raise ValueError("archive: unfinished week")
    days = []
    for name in _day_directories(hot_root):
        day = _parse_day(name)
        if monday <= day <= sunday and day < today:
            days.append(name)
    return days


def _add_day(tar, hot_root, day):
    """Adds regular files/directories only and refuses symlinks in the source day."""
    root = os.path.join(hot_root, day)
    if os.path.islink(root) or not os.path.isdir(root):
        raise ValueError("archive: unsafe day directory")
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs.sort()
        files.sort()
        for name in list(dirs):
            path = os.path.join(base, name)
            if os.path.islink(path):
                raise ValueError("archive: symlink in hot day")
            tar.add(path, arcname=os.path.relpath(path, hot_root), recursive=False)
        for name in files:
            path = os.path.join(base, name)
            if os.path.islink(path) or not os.path.isfile(path):
                raise ValueError("archive: unsafe hot file")
            tar.add(path, arcname=os.path.relpath(path, hot_root), recursive=False)


def _hash_file(path):
    """Streams SHA-256 in bounded chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_archive(hot_root, week, staging):
    """Builds one finished-week tar.xz atomically in SSD staging and hashes it."""
    days = _week_days(hot_root, week)
    if not days:
        raise ValueError("archive: no eligible days")
    if not os.path.isdir(staging) or os.path.islink(staging):
        raise OSError("archive: staging unavailable")
    name = "blackbox-%s.tar.xz" % week
    final = os.path.join(staging, name)
    temp = final + ".tmp"
    if os.path.lexists(temp):
        raise OSError("archive: staging temp exists")
    _write_archive_temp(temp, final, hot_root, days)
    return final, _hash_file(final)


def _write_archive_temp(temp, final, hot_root, days):
    """Writes and atomically promotes a private tar.xz staging file."""
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as raw:
            with lzma.LZMAFile(raw, mode="wb") as compressed:
                with tarfile.open(fileobj=compressed, mode="w|",
                                  format=tarfile.PAX_FORMAT) as tar:
                    for day in days:
                        _add_day(tar, hot_root, day)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temp, final)
    except (OSError, ValueError, tarfile.TarError, lzma.LZMAError):
        _cleanup_temp(temp)
        raise OSError("archive: build failed")


def _safe_destination(path):
    """True only for absent or regular non-symlink destinations."""
    if not os.path.lexists(path):
        return True
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        raise OSError("archive: destination unavailable")


def _write_sidecar(path, sha):
    """Creates a sidecar atomically without replacing a pre-existing record."""
    temp = path + ".tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(sha + "  " + os.path.basename(path[:-7]) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.link(temp, path)
    os.unlink(temp)


def _valid_archive_source(path, sha):
    if not SHA_RE.match(sha) or not os.path.isfile(path) or os.path.islink(path):
        return False
    name = os.path.basename(path)
    match = ARCHIVE_RE.match(name)
    if not match:
        return False
    try:
        _week_bounds(match.group(1))
    except ValueError:
        return False
    return True


def ship(path, sha, hdd_dir, run=subprocess.run):
    """Copies one archive through HDD temp, syncs, renames, verifies, then records SHA."""
    if not _valid_archive_source(path, sha):
        return False
    name = os.path.basename(path)
    final = os.path.join(hdd_dir, name)
    sidecar = final + ".sha256"
    if not _ship_targets_safe(hdd_dir, final, sidecar):
        return False
    if os.path.lexists(final):
        return _ship_existing(final, sidecar, sha, name, run)
    if os.path.lexists(sidecar):
        return False
    return _ship_new(path, sha, hdd_dir, final, sidecar, name, run)


def _ship_existing(final, sidecar, sha, name, run):
    if not _remote_matches(final, sha, run):
        return False
    if os.path.lexists(sidecar):
        return _sidecar_matches(sidecar, sha, name) and _sync_final(final, run)
    try:
        _write_sidecar(sidecar, sha)
    except OSError:
        return False
    return _sync_final(final, run)


def _ship_new(path, sha, hdd_dir, final, sidecar, name, run):
    temp = _create_hdd_temp(hdd_dir, os.path.basename(path))
    if not temp:
        return False
    if not _copy_sync(path, temp, run):
        return False
    if not _remote_matches(temp, sha, run):
        _cleanup_temp(temp)
        return False
    if not _promote_temp(temp, final):
        return False
    if not _remote_matches(final, sha, run):
        return False
    try:
        _write_sidecar(sidecar, sha)
    except OSError:
        return False
    return _sync_final(final, run)


def _sync_final(final, run):
    """Flush the published name and sidecar before acknowledging SSD deletion."""
    result = _run(run, ("timeout", str(COMMAND_TIMEOUT), "sync", "-f", final),
                  COMMAND_TIMEOUT + 5)
    return result is not None and result.returncode == 0


def _sidecar_matches(path, sha, archive_name):
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 256:
            return False
        with open(path, "r", encoding="ascii") as fh:
            return fh.read(257) == sha + "  " + archive_name + "\n"
    except (OSError, UnicodeError):
        raise OSError("archive: sidecar unavailable")


def _ship_targets_safe(hdd_dir, final, sidecar):
    return (not os.path.islink(hdd_dir) and os.path.isdir(hdd_dir) and
            _safe_destination(final) and _safe_destination(sidecar))


def _create_hdd_temp(hdd_dir, name):
    try:
        fd, path = tempfile.mkstemp(prefix="." + name + ".", suffix=".tmp",
                                    dir=hdd_dir)
        os.close(fd)
        return path
    except OSError:
        raise OSError("archive: HDD temp unavailable")


def _copy_sync(source, temp, run):
    copied = _run(run, ("timeout", str(SHIP_TIMEOUT), "cp", "--", source, temp),
                  SHIP_TIMEOUT + 5)
    if copied is None or copied.returncode != 0:
        _cleanup_temp(temp)
        return False
    synced = _run(run, ("timeout", str(SHIP_TIMEOUT), "sync", "-f", temp),
                  SHIP_TIMEOUT + 5)
    if synced is None or synced.returncode != 0:
        _cleanup_temp(temp)
        return False
    return True


def _promote_temp(temp, final):
    try:
        if os.path.islink(temp) or not os.path.isfile(temp):
            return False
        os.link(temp, final)
        os.unlink(temp)
        return True
    except OSError:
        _cleanup_temp(temp)
        return False


def _remote_matches(final, expected, run):
    result = _run(run, ("timeout", str(VERIFY_TIMEOUT), "sha256sum", final),
                  VERIFY_TIMEOUT + 5)
    if result is None or result.returncode != 0:
        return False
    fields = (result.stdout or "").split()
    return bool(fields and SHA_RE.match(fields[0]) and fields[0] == expected)


def _cleanup_temp(path):
    """Removes only a regular file at this operation's exact temporary name."""
    try:
        if stat.S_ISREG(os.lstat(path).st_mode):
            os.unlink(path)
    except OSError:
        return False
    return True


def _ensure_hdd_year(cfg, year):
    """Creates archive directories only below the configured mounted HDD path."""
    if not _hdd_root_valid(cfg):
        return None
    mount = os.path.abspath(cfg.hdd_mount)
    root = os.path.abspath(cfg.hdd_archive_root)
    relative = os.path.relpath(os.path.join(root, year), mount)
    current = mount
    for part in relative.split(os.sep):
        if part in ("", ".", ".."):
            return None
        current = os.path.join(current, part)
        if os.path.lexists(current):
            if os.path.islink(current) or not os.path.isdir(current):
                return None
        else:
            try:
                os.mkdir(current)
            except OSError:
                return None
    return current


def _hdd_root_valid(cfg):
    """Checks configured archive path ancestry without following symlinks."""
    mount = os.path.abspath(cfg.hdd_mount)
    root = os.path.abspath(cfg.hdd_archive_root)
    try:
        if os.path.islink(mount) or not os.path.isdir(mount):
            return False
        if os.path.commonpath((mount, root)) != mount:
            return False
        relative = os.path.relpath(root, mount)
    except (OSError, ValueError):
        return False
    current = mount
    for part in relative.split(os.sep):
        if part in ("", ".", ".."):
            return False
        current = os.path.join(current, part)
        if os.path.lexists(current) and (os.path.islink(current) or
                                          not os.path.isdir(current)):
            return False
    return True


def _event(catalog, week, kind, severity, reason):
    """Stores a fixed-reason archiver event without external stderr."""
    catalog.add_events([{"ts": int(time.time()), "source": "archiver", "kind": kind,
                         "subject": week, "severity": severity,
                         "detail": {"reason": reason}}])


def _source_fingerprint(hot_root, days):
    """Captures names, types, sizes, and mtimes for source files and dirs."""
    result = []
    for day in days:
        root = os.path.join(hot_root, day)
        if os.path.islink(root) or not os.path.isdir(root):
            raise OSError("archive: source changed")
        for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
            dirs.sort()
            files.sort()
            for name in dirs + files:
                path = os.path.join(base, name)
                info = os.lstat(path)
                if stat.S_ISLNK(info.st_mode):
                    raise OSError("archive: unsafe source")
                result.append((os.path.relpath(path, hot_root), info.st_mode,
                               info.st_size, info.st_mtime_ns))
    return tuple(result)


def _catalog_week(catalog, week):
    for row in catalog.archives():
        if row["week"] == week:
            return row
    return None


def _remove_week_days(hot_root, days):
    """Removes only validated week day directories, never following symlinks."""
    for day in days:
        path = os.path.join(hot_root, day)
        if DAY_RE.match(day) and not os.path.islink(path) and os.path.isdir(path):
            shutil.rmtree(path)


def archive_week(cfg, catalog, week, run=subprocess.run):
    """Builds, verifies, catalogs and only then removes a finished hot week."""
    try:
        _week_bounds(week)
        busy = hdd_busy(cfg, run)
        if busy:
            return {"status": "deferred", "reason": "busy: " + busy}
        if not hdd_alive(cfg, run):
            return {"status": "deferred", "reason": "hdd unavailable"}
        return _archive_week_data(cfg, catalog, week, run)
    except (OSError, ValueError, sqlite3.Error, tarfile.TarError, lzma.LZMAError):
        return {"status": "failed", "reason": FIXED_ERROR}


def _archive_week_data(cfg, catalog, week, run):
    hot_root = os.path.join(cfg.ssd_root, "hot")
    days = _week_days(hot_root, week)
    if not days:
        return {"status": "failed", "reason": "no eligible days"}
    source_state = _source_fingerprint(hot_root, days)
    staging = os.path.join(cfg.ssd_root, "staging")
    if not os.path.isdir(staging):
        os.makedirs(staging)
    archive, sha = build_archive(hot_root, week, staging)
    if _source_fingerprint(hot_root, days) != source_state:
        return {"status": "failed", "reason": "source changed"}
    prior = _catalog_week(catalog, week)
    if prior is not None and prior["sha256"] != sha:
        return {"status": "failed", "reason": "archive record conflict"}
    year_dir = _ensure_hdd_year(cfg, week[:4])
    if year_dir is None:
        raise OSError("archive: unsafe HDD root")
    if not ship(archive, sha, year_dir, run):
        _event(catalog, week, "verify_failed", "warn", FIXED_ERROR)
        return {"status": "failed", "reason": FIXED_ERROR}
    if _source_fingerprint(hot_root, days) != source_state:
        return {"status": "failed", "reason": "source changed"}
    row = {"week": week,
           "path": os.path.join(year_dir, os.path.basename(archive)),
           "sha256": sha, "first_day": days[0], "last_day": days[-1],
           "created": int(time.time()), "verified": True}
    catalog.add_archive(row)
    if _source_fingerprint(hot_root, days) != source_state:
        return {"status": "failed", "reason": "source changed"}
    _remove_week_days(hot_root, days)
    return {"status": "shipped", "reason": "verified"}


def _archive_pair(path, year, today, retention_days):
    """Recognizes a strict archive name paired with a regular sidecar older than retention."""
    name = os.path.basename(path)
    match = ARCHIVE_RE.match(name)
    if not match or match.group(1)[:4] != year:
        return None
    sidecar = path + ".sha256"
    if os.path.islink(path) or os.path.islink(sidecar):
        return None
    if not os.path.isfile(path) or not os.path.isfile(sidecar):
        return None
    try:
        _monday, sunday = _week_bounds(match.group(1))
    except ValueError:
        return None
    return (path, sidecar) if (today - sunday).days > retention_days else None


def prune_hdd(hdd_root, today, retention_days=365):
    """Prunes only strict archive/sidecar pairs older than retention, without following links."""
    current = _today_date(today)
    if not isinstance(retention_days, int) or retention_days < 0:
        raise ValueError("archive: invalid retention")
    if os.path.islink(hdd_root) or not os.path.isdir(hdd_root):
        return []
    return _prune_years(hdd_root, current, retention_days)


def _prune_years(root, today, retention_days):
    removed = []
    for year in sorted(os.listdir(root)):
        path = os.path.join(root, year)
        if re.match(r"^\d{4}$", year) and not os.path.islink(path) and os.path.isdir(path):
            removed.extend(_prune_year(path, year, today, retention_days))
    return removed


def _prune_year(path, year, today, retention_days):
    removed = []
    for name in sorted(os.listdir(path)):
        pair = _archive_pair(os.path.join(path, name), year, today, retention_days)
        if pair:
            os.unlink(pair[0])
            os.unlink(pair[1])
            removed.append(pair[0])
    return removed


def worker_main():
    """Worker-only production entrypoint; mount guard precedes every HDD write."""
    from .archive_supervisor import await_worker_authorization
    from .archive_supervisor import worker_marker_path

    cfg = load_config()
    if not await_worker_authorization(worker_marker_path(cfg), cfg.proc_root):
        return 2
    if not os.path.ismount(cfg.hdd_mount):
        return 3
    if not _hdd_root_valid(cfg):
        return 4
    catalog = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    try:
        today = datetime.datetime.utcnow().date().isoformat()
        failed = False
        for week in weeks_due(os.path.join(cfg.ssd_root, "hot"), today):
            if archive_week(cfg, catalog, week, subprocess.run)["status"] == "failed":
                failed = True
        if not hdd_busy(cfg, subprocess.run) and hdd_alive(cfg, subprocess.run):
            prune_hdd(cfg.hdd_archive_root, today, cfg.hdd_retention_days)
        if failed:
            return 5
    finally:
        catalog.close()
    return 0
