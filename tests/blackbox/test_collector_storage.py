"""OBS-1, задача 7 — хранилище сборщика: физический предел запаса, fail
closed, честный возобновляемый перенос > 10000 записей, подтверждение только
после коммита. Настоящие SQLite-файлы во временном каталоге, без сети."""
import json
import os
import sqlite3

import pytest

from blackbox import collector_storage
from blackbox.config import Config
from blackbox.store import Catalog, write_heartbeat

T0 = 1791861274                 # 2026-10-13 03:14:34 UTC
CAP = 320 << 10


def _cfg(tmp_path, cap=CAP):
    return Config(ssd_root=str(tmp_path / "ssd"),
                  fallback_root=str(tmp_path / "fb"),
                  ssd_mount=str(tmp_path / "mnt"),
                  proc_root=str(tmp_path / "proc"),
                  fallback_cap_bytes=cap)


def _event(ts, text="x" * 200):
    return {"ts": ts, "source": "probe", "kind": "k", "subject": "s",
            "severity": "info", "detail": {"msg": text}}


def _count(cfg, table):
    path = os.path.join(cfg.fallback_root, "catalog.db")
    if not os.path.isfile(path):
        return 0
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT count(*) FROM " + table).fetchone()[0]
    finally:
        conn.close()


def _size(cfg):
    db = os.path.join(cfg.fallback_root, "catalog.db")
    paths = (db, db + "-wal", db + "-shm",
             os.path.join(cfg.fallback_root, "heartbeat"))
    return sum(os.path.getsize(path) for path in paths if os.path.isfile(path))


def _seed(path, events, minutes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Catalog(path).close()
    conn = sqlite3.connect(path)
    with conn:
        conn.executemany(
            "INSERT INTO event (ts, source, kind, subject, severity, detail) "
            "VALUES (?,?,?,?,?,?)",
            [(T0 + index, "docker", "die", "c", "crit",
              json.dumps({"i": index})) for index in range(events)])
        conn.executemany("INSERT INTO minute (ts, data) VALUES (?,?)",
                         [(T0 + index, json.dumps({"i": index}))
                          for index in range(minutes)])
    conn.close()


def test_fallback_cap_keeps_physical_size_after_repeated_fills(tmp_path):
    """Повторные заполнения: файл базы и WAL физически уменьшаются, предел держится."""
    cfg = _cfg(tmp_path)
    store = collector_storage.Storage(cfg, T0, ismount=lambda path: False)
    heartbeat = os.path.join(cfg.fallback_root, "heartbeat")
    for round_no in range(4):
        for index in range(500):
            store.buffer_event(_event(T0 + round_no * 1000 + index))
        store.add_minute({"ts": T0 + round_no * 1000 + 499, "count": 1}, T0)
        write_heartbeat(heartbeat, "boot", T0, {})
        store.flush(T0 + round_no * 10)
        assert _size(cfg) <= cfg.fallback_cap_bytes
    assert _count(cfg, "event") > 0 and _count(cfg, "minute") > 0
    store.close()


def test_fallback_cap_below_minimum_fails_closed(tmp_path):
    """Предел ниже минимума: события/минуты не пишутся вовсе, сборщик жив."""
    cfg = _cfg(tmp_path, cap=64 << 10)
    store = collector_storage.Storage(cfg, T0, ismount=lambda path: False)
    for index in range(100):
        store.buffer_event(_event(T0 + index))
    store.add_minute({"ts": T0, "count": 1}, T0)
    store.flush(T0 + 10)
    assert (store.mode, _count(cfg, "event"), _count(cfg, "minute")) == (
        "fallback", 0, 0)
    store.close()


def test_unreclaimable_fallback_cap_disables_future_writes(tmp_path, monkeypatch):
    """Невозможность ужать базу переводит кольцо в fail-closed до следующих записей."""
    cfg = _cfg(tmp_path)
    store = collector_storage.Storage(cfg, T0, ismount=lambda path: False)
    monkeypatch.setattr(collector_storage, "_file_size",
                        lambda path: cfg.fallback_cap_bytes * 2)
    store.enforce_cap()
    assert not store.ring.writable
    store.add_minute({"ts": T0, "count": 1}, T0)
    store.buffer_event(_event(T0))
    store.flush(T0 + 10)
    assert (_count(cfg, "event"), _count(cfg, "minute")) == (0, 0)
    store.close()


def test_migration_fair_resumable_beyond_10000(tmp_path):
    """> 10000 событий и минут: шаги ограничены, обе таблицы двигаются, перенос
    переживает перезапуск и не дублирует записи."""
    cfg = _cfg(tmp_path, cap=1 << 20)
    fallback = os.path.join(cfg.fallback_root, "catalog.db")
    _seed(fallback, 10020, 10020)
    store = collector_storage.Storage(cfg, T0, ismount=lambda path: True)
    store.flush(T0 + 10)
    left = (_count(cfg, "event"), _count(cfg, "minute"))
    assert 0 < left[0] < 10020 and 0 < left[1] < 10020
    store.close()
    store = collector_storage.Storage(cfg, T0, ismount=lambda path: True)
    for step in range(2, 12):
        store.flush(T0 + step * 10)
    assert (_count(cfg, "event"), _count(cfg, "minute")) == (0, 0)
    catalog = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    events = catalog.events(T0 - 1, T0 + 20000, source="docker")
    minutes = catalog.minutes(T0 - 1, T0 + 20000)
    assert (len(events), len(minutes)) == (10020, 10020)
    store.flush(T0 + 500)
    assert (len(catalog.events(T0 - 1, T0 + 20000, source="docker")),
            len(catalog.minutes(T0 - 1, T0 + 20000))) == (10020, 10020)
    catalog.close()
    store.close()


def test_migration_acks_source_only_after_destination_commit(tmp_path, monkeypatch):
    """Отказ после коммита, но до подтверждения: повтор не дублирует события."""
    cfg = _cfg(tmp_path, cap=1 << 20)
    fallback = os.path.join(cfg.fallback_root, "catalog.db")
    _seed(fallback, 12, 0)
    os.makedirs(cfg.ssd_root, exist_ok=True)
    catalog = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    migration = collector_storage.Migration(catalog, fallback)

    def broken(conn, table, rowids):
        raise sqlite3.OperationalError("locked")

    real = collector_storage._delete_rowids
    monkeypatch.setattr(collector_storage, "_delete_rowids", broken)
    with pytest.raises(sqlite3.OperationalError):
        migration.step()
    assert _count(cfg, "event") == 12              # подтверждения не было
    monkeypatch.setattr(collector_storage, "_delete_rowids", real)
    migration.step()
    assert _count(cfg, "event") == 0
    assert len(catalog.events(T0 - 1, T0 + 1000)) == 12
    catalog.close()
