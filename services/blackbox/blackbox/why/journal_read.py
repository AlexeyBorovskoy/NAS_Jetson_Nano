"""Bounded readers and canonical timestamps for saved OBS-1 journals."""
import datetime
import gzip
import io
import lzma
import os
import re

STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?)(Z|[+-]\d\d:?\d\d)")
LOGGER = re.compile(r"^\S+\s+([^\s\[]+)(?:\[\d+\])?:\s*(.*)$")
READ_LIMIT = 4 << 20
MAX_LINES = 20000


def _parse_stamp(value):
    if value.endswith("Z"):
        value = value[:-1] + "+0000"
    if len(value) >= 6 and value[-3] == ":":
        value = value[:-3] + value[-2:]
    formats = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")
    for fmt in formats:
        try:
            parsed = datetime.datetime.strptime(value, fmt)
            return int(calendar_time(parsed))
        except ValueError:
            pass
    return None


def calendar_time(value):
    return value.timestamp()


def normalize_line(line):
    match = STAMP.match(line)
    if not match:
        return None, line.strip()
    ts = _parse_stamp(match.group(1) + match.group(2))
    rest = line[match.end():].strip()
    logger = LOGGER.match(rest)
    if logger:
        rest = "%s: %s" % (logger.group(1), logger.group(2))
    return ts, rest


def _read(path, compressed):
    opener = lzma.open if compressed == "xz" else gzip.open if compressed == "gz" else open
    try:
        with opener(path, "rb") as stream:
            data = stream.read(READ_LIMIT + 1)
        if len(data) > READ_LIMIT:
            return None
        lines = []
        for line in io.StringIO(data.decode("utf-8", "replace")):
            if len(lines) >= MAX_LINES:
                return None
            lines.append(line.rstrip("\r\n"))
        return lines
    except (OSError, EOFError, lzma.LZMAError):
        return None


def read_journal(path):
    suffix = "xz" if path.endswith(".xz") else None
    lines = _read(path, suffix)
    if lines is None:
        return None
    return [normalize_line(line) for line in lines]


def read_container_log(path, container):
    lines = _read(path, "gz")
    if lines is None:
        return None
    result = []
    for line in lines:
        result.append(normalize_line(line))
    return result


def day_path(root, day, filename):
    path = os.path.join(root, day, filename)
    return path if os.path.isfile(path) and not os.path.islink(path) else None
