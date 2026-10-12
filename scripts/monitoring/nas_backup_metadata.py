#!/usr/bin/env python3
"""Publish stat-only database dump metadata atomically; never open dumps."""
import argparse
import json
import os
import stat
import tempfile
import time
from pathlib import Path


def collect(source: Path) -> dict:
    result = {'schema': 1, 'generated_at': time.time(), 'available': False, 'dumps': []}
    try:
        if not source.is_dir():
            return result
        for db in ('nextcloud', 'immich'):
            files = []
            for path in source.glob(db + '_*.sql.gz'):
                info = path.lstat()
                if stat.S_ISREG(info.st_mode):
                    files.append(info)
            newest = max(files, key=lambda info: info.st_mtime) if files else None
            result['dumps'].append({'db': db, 'mtime': newest.st_mtime if newest else None,
                                    'size_bytes': newest.st_size if newest else 0, 'count_total': len(files)})
        result['available'] = True
    except OSError:
        result['dumps'] = []
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=args.output.parent, prefix='.backup-metadata-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(collect(args.source), stream)
        os.chmod(temporary, 0o644)
        os.replace(temporary, args.output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    main()
