"""Metadata freshness and source failure must never imply healthy backups."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    spec = importlib.util.spec_from_file_location('backup_metadata_test_module', ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader = load('services/nas_jetson_nano-api/app/services/backup_metadata.py')
collector = load('scripts/monitoring/nas_backup_metadata.py')


def snapshot():
    return {'schema': 1, 'generated_at': 10000, 'available': True, 'dumps': [
        {'db': db, 'mtime': 6400, 'size_bytes': 1048576, 'count_total': 7}
        for db in ('nextcloud', 'immich')]}


def read(tmp_path, data, now=10000):
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(data))
    return reader.read_snapshot(str(path), now=now)


def test_valid_snapshot_age_recomputed(tmp_path):
    result = read(tmp_path, snapshot(), now=10900)
    assert result['available']
    assert result['dumps'][0]['age_hours'] == 1
    assert result['dumps'][0]['size_mb'] == 1


@pytest.mark.parametrize('now', [10901, 9939])
def test_stale_or_future_is_unknown(tmp_path, now):
    assert read(tmp_path, snapshot(), now)['available'] is False


@pytest.mark.parametrize('change', [
    {'available': False}, {'schema': 2}, {'dumps': []},
    {'generated_at': float('nan')}, {'generated_at': '10000'},
    {'dumps': [{'db': 'nextcloud'}, {'db': 'nextcloud'}]},
])
def test_invalid_snapshot_is_unknown(tmp_path, change):
    data = snapshot()
    data.update(change)
    assert read(tmp_path, data)['available'] is False


@pytest.mark.parametrize('raw', ['{', '[]', '{}', 'x' * 65537], ids=['broken', 'list', 'empty', 'oversized'])
def test_malformed_or_oversized_is_unknown(tmp_path, raw):
    path = tmp_path / 'snapshot.json'
    path.write_text(raw)
    assert reader.read_snapshot(str(path), now=10000)['available'] is False


def test_actual_missing_dump_differs_from_unknown(tmp_path):
    data = snapshot()
    data['dumps'][0].update(mtime=None, size_bytes=0, count_total=0)
    result = read(tmp_path, data)
    assert result['available']
    assert result['dumps'][0]['age_hours'] is None


def test_collector_never_reads_dump_contents(tmp_path, monkeypatch):
    dump = tmp_path / 'nextcloud_test.sql.gz'
    dump.write_bytes(b'synthetic')
    def forbidden(*args, **kwargs):
        raise AssertionError('dump contents must not be read')
    monkeypatch.setattr(Path, 'open', forbidden)
    result = collector.collect(tmp_path)
    assert result['available']
    assert result['dumps'][0]['size_bytes'] == 9
    assert result['dumps'][1]['mtime'] is None


def test_missing_source_is_unknown(tmp_path):
    assert collector.collect(tmp_path / 'absent')['available'] is False
