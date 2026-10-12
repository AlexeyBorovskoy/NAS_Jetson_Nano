"""Read bounded, fresh host metadata without access to database contents."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path


# Split per the metrics ratchet (docs/audit/2026-10-02_code_audit/PLAN.ru.md
# "Храповик", R3 new-function rule): the original `read_snapshot` body had
# cc=27/loc=38. Each helper below does exactly one validation step from the
# original inline sequence and raises the same ValueError on failure; none of
# them catch anything themselves, so `read_snapshot`'s own try/except still
# sees every failure and returns the same "unavailable" shape. Behaviour and
# exact error strings are unchanged — only the structure moved.

def _load_raw_json(path: str) -> dict:
    """Read at most one byte past the size cap, then parse JSON."""
    with Path(path).open('rb') as fh:
        raw = fh.read(65537)
    if len(raw) > 65536:
        raise ValueError('oversized snapshot')
    return json.loads(raw)


def _validate_envelope(data: dict, now: float) -> list:
    """Check freshness, schema and shape; return the raw `dumps` list."""
    created = data['generated_at']
    if type(created) not in (int, float) or not math.isfinite(created) or not -60 <= now - created <= 900:
        raise ValueError('stale snapshot')
    if data.get('schema') != 1 or data.get('available') is not True:
        raise ValueError('unavailable source')
    items = data['dumps']
    if not isinstance(items, list) or len(items) != 2:
        raise ValueError('invalid dumps')
    return items


def _find_dump_item(items: list, db: str) -> dict:
    """Return the single entry for `db`, or raise if missing/duplicated."""
    matches = [item for item in items if isinstance(item, dict) and item.get('db') == db]
    if len(matches) != 1:
        raise ValueError('missing database')
    return matches[0]


def _validate_dump_counts(item: dict) -> tuple:
    """Pull mtime/size/count out of one dump entry; check size/count types."""
    modified, size, count = item['mtime'], item['size_bytes'], item['count_total']
    if type(count) is not int or count < 0 or type(size) is not int or size < 0:
        raise ValueError('invalid size/count')
    return modified, size, count


def _missing_dump_age(count: int, size: int) -> None:
    """A dump never taken: `mtime` is None, size/count must both be zero."""
    if count != 0 or size != 0:
        raise ValueError('inconsistent missing dump')
    return None


def _present_dump_age(modified: float, count: int, now: float) -> int:
    """Age in whole hours for a dump that was actually taken."""
    if type(modified) not in (int, float) or not math.isfinite(modified) or modified > now + 60 or count < 1:
        raise ValueError('invalid timestamp')
    return max(0, int((now - modified) / 3600))


def _dump_age_hours(modified, count: int, size: int, now: float):
    """None for a never-taken dump, else its age in hours."""
    if modified is None:
        return _missing_dump_age(count, size)
    return _present_dump_age(modified, count, now)


def _parse_dump_item(items: list, db: str, now: float) -> dict:
    """Validate and shape the `db` entry of `items` into the public record."""
    item = _find_dump_item(items, db)
    modified, size, count = _validate_dump_counts(item)
    age = _dump_age_hours(modified, count, size, now)
    return {'db': db, 'file': None if age is None else 'host-metadata',
           'size_mb': round(size / 1024**2, 1), 'age_hours': age, 'count_total': count}


def read_snapshot(path: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    try:
        data = _load_raw_json(path)
        items = _validate_envelope(data, now)
        result = [_parse_dump_item(items, db, now) for db in ('nextcloud', 'immich')]
        return {'available': True, 'source': 'host-metadata', 'dumps': result}
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return {'available': False, 'reason': 'backup metadata unavailable, stale or invalid', 'dumps': []}
