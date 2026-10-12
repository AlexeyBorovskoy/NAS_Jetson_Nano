"""Read bounded, fresh host metadata without access to database contents."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path


def read_snapshot(path: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    try:
        with Path(path).open('rb') as fh:
            raw = fh.read(65537)
        if len(raw) > 65536:
            raise ValueError('oversized snapshot')
        data = json.loads(raw)
        created = data['generated_at']
        if type(created) not in (int, float) or not math.isfinite(created) or not -60 <= now - created <= 900:
            raise ValueError('stale snapshot')
        if data.get('schema') != 1 or data.get('available') is not True:
            raise ValueError('unavailable source')
        items = data['dumps']
        if not isinstance(items, list) or len(items) != 2:
            raise ValueError('invalid dumps')
        result = []
        for db in ('nextcloud', 'immich'):
            matches = [item for item in items if isinstance(item, dict) and item.get('db') == db]
            if len(matches) != 1:
                raise ValueError('missing database')
            item = matches[0]
            modified, size, count = item['mtime'], item['size_bytes'], item['count_total']
            if type(count) is not int or count < 0 or type(size) is not int or size < 0:
                raise ValueError('invalid size/count')
            if modified is None:
                if count != 0 or size != 0:
                    raise ValueError('inconsistent missing dump')
                age = None
            else:
                if type(modified) not in (int, float) or not math.isfinite(modified) or modified > now + 60 or count < 1:
                    raise ValueError('invalid timestamp')
                age = max(0, int((now - modified) / 3600))
            result.append({'db': db, 'file': None if age is None else 'host-metadata',
                           'size_mb': round(size / 1024**2, 1), 'age_hours': age, 'count_total': count})
        return {'available': True, 'source': 'host-metadata', 'dumps': result}
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return {'available': False, 'reason': 'backup metadata unavailable, stale or invalid', 'dumps': []}
