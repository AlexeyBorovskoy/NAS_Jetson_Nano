"""Bounded, allowlisted read-only extraction for why evidence."""
import hashlib
import datetime
import lzma
import os
import re
import shutil
import stat
import tarfile
import tempfile

ARCHIVE_RE = re.compile(r"^blackbox-\d{4}-W\d{2}\.tar\.xz$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_MEMBERS = 4096
MAX_TOTAL = 512 << 20
MAX_FILE = 64 << 20
MAX_ARCHIVE = 256 << 20


def _inside(root, path):
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    return os.path.commonpath((root, path)) == root


def _hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            data = stream.read(1 << 20)
            if not data:
                return digest.hexdigest()
            digest.update(data)


def _archive_path(cfg, row):
    path = row.get("path") or ""
    if not ARCHIVE_RE.match(os.path.basename(path)) or not _inside(cfg.hdd_archive_root, path):
        raise ValueError("unsafe archive path")
    if not os.path.isfile(path) or os.path.islink(path):
        raise ValueError("archive unavailable")
    if os.path.getsize(path) > MAX_ARCHIVE:
        raise ValueError("archive too large")
    expected = row.get("sha256")
    if expected and _hash(path) != expected:
        raise ValueError("archive hash mismatch")
    return path


def _member_name(member, day, week_days):
    name = member.name.replace("\\", "/").rstrip("/")
    _validate_member(member, name)
    if name == day:
        return None
    if name.startswith(day + "/"):
        return _selected_member_tail(name, day)
    if _is_safe_other_day(name, week_days):
        return None
    raise ValueError("archive member outside week")


def _validate_member(member, name):
    if not _safe_member_path(name):
        raise ValueError("unsafe archive member")
    if not _safe_member_type(member):
        raise ValueError("unsafe archive member type")
    if member.size < 0 or member.size > MAX_FILE:
        raise ValueError("archive member too large")


def _selected_member_tail(name, day):
    tail = _day_relative(name, day)
    if not tail or not _allowed_tail(tail):
        return None
    return tail


def _is_safe_other_day(name, week_days):
    parts = name.split("/")
    day_name = parts[0]
    return day_name in week_days and (len(parts) == 1 or len(parts) > 1)


def _safe_member_path(name):
    parts = name.split("/")
    return bool(name) and not name.startswith("/") and ".." not in parts and "" not in parts


def _day_relative(name, day):
    prefix = day + "/"
    return name[len(prefix):] if name.startswith(prefix) else None


def _safe_member_type(member):
    return (member.isdir() or member.isfile()) and not member.issparse()


def _allowed_tail(tail):
    if tail in ("metrics.db", "procs.db", "journal.log", "journal.log.xz"):
        return True
    parts = tail.split("/")
    return (len(parts) == 2 and parts[0] == "containers" and
            parts[1].endswith(".log.gz"))


def _extract_selected(archive, day, target):
    total = count = 0
    seen = set()
    week_days = _week_days(archive)
    with tarfile.open(archive, "r|xz") as tar:
        for member in tar:
            count += 1
            if count > MAX_MEMBERS:
                raise ValueError("archive member count exceeded")
            total += member.size
            if total > MAX_TOTAL:
                raise ValueError("archive total size exceeded")
            tail = _member_name(member, day, week_days)
            if tail is None or member.isdir():
                continue
            if tail in seen:
                raise ValueError("duplicate archive path")
            seen.add(tail)
            if shutil.disk_usage(target).free < member.size:
                raise ValueError("archive staging space exceeded")
            _copy_member(tar, member, target, tail)
    if count == 0:
        raise ValueError("archive has no allowed evidence")


def _week_days(archive):
    match = re.match(r"^blackbox-(\d{4})-W(\d{2})\.tar\.xz$",
                     os.path.basename(archive))
    year, week = int(match.group(1)), int(match.group(2))
    jan4 = datetime.date(year, 1, 4)
    monday = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
    monday += datetime.timedelta(weeks=week - 1)
    return set((monday + datetime.timedelta(days=offset)).isoformat()
               for offset in range(7))


def _copy_member(tar, member, target, tail):
    path = os.path.join(target, *tail.split("/"))
    if not _inside(target, path):
        raise ValueError("archive path escaped staging")
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent, mode=0o700)
    source = tar.extractfile(member)
    if source is None:
        raise ValueError("archive member unreadable")
    written = 0
    with source, open(path, "xb") as dest:
        while written < member.size:
            block = source.read(min(1 << 20, member.size - written))
            if not block:
                break
            dest.write(block)
            written += len(block)
    if written != member.size:
        raise ValueError("archive member size mismatch")


def extract_day(cfg, row, day, ssd_available=None):
    """Return (private temp dir, reason); caller owns cleanup in finally."""
    if not DAY_RE.match(day):
        return None, "invalid archive day"
    target = None
    try:
        if ssd_available is False:
            raise ValueError("SSD unavailable")
        if ssd_available is True and not os.path.ismount(cfg.ssd_mount):
            raise ValueError("SSD mount unavailable")
        archive = _archive_path(cfg, row)
        tmp_root = os.path.join(cfg.ssd_root, "tmp")
        if os.path.islink(cfg.ssd_root) or os.path.islink(tmp_root):
            raise ValueError("unsafe SSD staging")
        if not os.path.isdir(tmp_root):
            os.makedirs(tmp_root, mode=0o700)
        target = tempfile.mkdtemp(prefix="why-", dir=tmp_root)
        _extract_selected(archive, day, target)
        return target, None
    except (OSError, ValueError, tarfile.TarError, EOFError, lzma.LZMAError):
        if target:
            shutil.rmtree(target, ignore_errors=True)
        return None, "архив повреждён или небезопасен"
