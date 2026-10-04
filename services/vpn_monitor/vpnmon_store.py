"""Учёт VPN и нагрузки VPS: SQLite и учёт приращений (спецификация 2026-10-04 §6).

Функции record_*, set_*, add_event и purge_old не делают commit: транзакцией
владеет вызывающий (`with db:`), чтобы один замер писался целиком или никак.
"""
import json
import os
import sqlite3

HOUR = 3600
DAY = 86400
RETENTION_DAYS = 400
MAX_RATE_INTERVAL = 300  # сек.: интервал длиннее — пропуск сбора, скорость не считаем
HOST_COUNTERS = ("wan", "awg", "xray")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS peers (
    pubkey TEXT PRIMARY KEY, name TEXT NOT NULL, vpn_ip TEXT,
    first_seen INTEGER NOT NULL, last_handshake INTEGER NOT NULL DEFAULT 0, removed_at INTEGER);
CREATE TABLE IF NOT EXISTS peer_state (
    pubkey TEXT PRIMARY KEY, rx INTEGER NOT NULL, tx INTEGER NOT NULL,
    ts REAL NOT NULL, epoch TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS peer_hourly (
    pubkey TEXT NOT NULL, hour_utc INTEGER NOT NULL, rx INTEGER NOT NULL DEFAULT 0,
    tx INTEGER NOT NULL DEFAULT 0, peak_bps REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (pubkey, hour_utc));
CREATE TABLE IF NOT EXISTS host_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS host_hourly (
    hour_utc INTEGER PRIMARY KEY, samples INTEGER NOT NULL DEFAULT 0,
    cpu_n INTEGER NOT NULL DEFAULT 0, cpu_sum REAL NOT NULL DEFAULT 0,
    cpu_max REAL NOT NULL DEFAULT 0, mem_max INTEGER NOT NULL DEFAULT 0,
    mem_total INTEGER NOT NULL DEFAULT 0, load_max REAL NOT NULL DEFAULT 0,
    disk_pct REAL NOT NULL DEFAULT 0, wan_rx INTEGER NOT NULL DEFAULT 0,
    wan_tx INTEGER NOT NULL DEFAULT 0, awg_rx INTEGER NOT NULL DEFAULT 0,
    awg_tx INTEGER NOT NULL DEFAULT 0, xray_rx INTEGER NOT NULL DEFAULT 0,
    xray_tx INTEGER NOT NULL DEFAULT 0, conntrack_max INTEGER NOT NULL DEFAULT 0,
    awg_miss INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (ts INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts);
"""

_HOST_COLS = ("cpu_n", "cpu_sum", "cpu_max", "mem_max", "mem_total", "load_max", "disk_pct",
              "wan_rx", "wan_tx", "awg_rx", "awg_tx", "xray_rx", "xray_tx", "conntrack_max",
              "awg_miss")
_HOST_MERGE = {"cpu_max": "MAX", "mem_max": "MAX", "load_max": "MAX", "conntrack_max": "MAX",
               "mem_total": "SET", "disk_pct": "SET"}


def _host_upsert_sql():
    sets = []
    for col in _HOST_COLS:
        how = _HOST_MERGE.get(col, "ADD")
        if how == "MAX":
            sets.append("%s=MAX(%s, excluded.%s)" % (col, col, col))
        elif how == "SET":
            sets.append("%s=excluded.%s" % (col, col))
        else:
            sets.append("%s=%s+excluded.%s" % (col, col, col))
    return ("INSERT INTO host_hourly (hour_utc, samples, %s) VALUES (?, 1, %s) "
            "ON CONFLICT(hour_utc) DO UPDATE SET samples=samples+1, %s"
            % (", ".join(_HOST_COLS), ", ".join("?" * len(_HOST_COLS)), ", ".join(sets)))


_HOST_UPSERT = _host_upsert_sql()


def open_db(path):
    """Открыть (и при нужде создать) БД. Новый файл создаётся с правами 0600."""
    if not os.path.exists(path):
        os.close(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600))
    db = sqlite3.connect(path, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1')")
    db.commit()
    return db


def get_meta(db, key, default=None):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(db, key, value):
    db.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def get_state(db):
    return dict(db.execute("SELECT key, value FROM host_state"))


def set_state(db, values):
    db.executemany("INSERT INTO host_state (key, value) VALUES (?, ?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   [(k, str(v)) for k, v in values.items()])


def add_event(db, ts, kind, detail=None):
    db.execute("INSERT INTO events (ts, kind, detail) VALUES (?, ?, ?)",
               (int(ts), kind, json.dumps(detail or {}, ensure_ascii=False)))


def hour_of(ts):
    return int(ts // HOUR) * HOUR


def counter_delta(prev, cur, same_epoch):
    """Прирост накопительного счётчика.

    prev=None — первый замер: точка отсчёта, прирост 0. Другая эпоха (перезагрузка,
    перезапуск контейнера) или уменьшение счётчика — сброс: прирост = cur.
    """
    if prev is None:
        return 0
    if not same_epoch or cur < prev:
        return cur
    return cur - prev


def minute_rate(nbytes, elapsed):
    """Бит/с за интервал между замерами; None, если интервал не годится для скорости."""
    if elapsed <= 0 or elapsed > MAX_RATE_INTERVAL:
        return None
    return nbytes * 8.0 / elapsed


def record_peers(db, now, peers, names, epoch):
    """Учёт одного замера пиров awg0. epoch = «boot_id|StartedAt контейнера»."""
    first_run = get_meta(db, "monitoring_start") is None
    if first_run:
        set_meta(db, "monitoring_start", int(now))
    for key, peer in peers.items():
        _upsert_peer(db, now, key, peer, names.get(key))
        _account_peer(db, now, key, peer, (epoch, first_run))
    _mark_removed(db, now, set(peers))


def _upsert_peer(db, now, key, peer, name):
    row = db.execute("SELECT name, last_handshake FROM peers WHERE pubkey=?", (key,)).fetchone()
    if row is None:
        db.execute("INSERT INTO peers (pubkey, name, vpn_ip, first_seen, last_handshake) "
                   "VALUES (?, ?, ?, ?, ?)",
                   (key, name or "ключ " + key[:8], peer["vpn_ip"], int(now), peer["handshake"]))
        return
    db.execute("UPDATE peers SET name=?, vpn_ip=?, last_handshake=?, removed_at=NULL WHERE pubkey=?",
               (name or row[0], peer["vpn_ip"], max(row[1], peer["handshake"]), key))


def _account_peer(db, now, key, peer, run):
    st = db.execute("SELECT rx, tx, ts, epoch FROM peer_state WHERE pubkey=?", (key,)).fetchone()
    drx, dtx, rate = _peer_increment(st, now, peer, run)
    db.execute("INSERT INTO peer_state (pubkey, rx, tx, ts, epoch) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(pubkey) DO UPDATE SET rx=excluded.rx, tx=excluded.tx, "
               "ts=excluded.ts, epoch=excluded.epoch", (key, peer["rx"], peer["tx"], now, run[0]))
    if drx or dtx:
        db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?) "
                   "ON CONFLICT(pubkey, hour_utc) DO UPDATE SET rx=rx+excluded.rx, "
                   "tx=tx+excluded.tx, peak_bps=MAX(peak_bps, excluded.peak_bps)",
                   (key, hour_of(now), drx, dtx, rate or 0.0))


def _peer_increment(st, now, peer, run):
    """(прирост rx, прирост tx, скорость бит/с или None) относительно прошлого замера.

    run = (эпоха, первый ли это замер учёта вообще).
    """
    epoch, first_run = run
    if st is None:
        base = None if first_run else 0  # пир появился после старта учёта — счётчик весь новый
        return counter_delta(base, peer["rx"], True), counter_delta(base, peer["tx"], True), None
    prev_rx, prev_tx, prev_ts, prev_epoch = st
    elapsed = now - prev_ts
    if elapsed <= 0:  # время пошло назад: замер становится новой точкой отсчёта (§8)
        return 0, 0, None
    same = prev_epoch == epoch
    drx = counter_delta(prev_rx, peer["rx"], same)
    dtx = counter_delta(prev_tx, peer["tx"], same)
    clean = same and peer["rx"] >= prev_rx and peer["tx"] >= prev_tx
    return drx, dtx, minute_rate(drx + dtx, elapsed) if clean else None


def _mark_removed(db, now, present):
    for (key,) in db.execute("SELECT pubkey FROM peers WHERE removed_at IS NULL").fetchall():
        if key not in present:
            db.execute("UPDATE peers SET removed_at=? WHERE pubkey=?", (int(now), key))


def record_host(db, now, host):
    """Учёт одного замера хоста: события, приращения, часовая строка, новое состояние."""
    st = get_state(db)
    _host_events(db, now, st, host)
    deltas = {name: _host_counter_delta(st, name, host["counters"].get(name))
              for name in HOST_COUNTERS}
    _add_host_hour(db, hour_of(now), host, _cpu_pct(st, host), deltas)
    set_state(db, _host_state(now, host))


def _host_events(db, now, st, host):
    old_boot = st.get("boot_id")
    if old_boot and old_boot != host["boot_id"]:
        add_event(db, now, "vps_down", {"from": float(st["ts"]), "to": host["btime"],
                                        "reason": host.get("shutdown_reason")})
    for name, started in host["started"].items():
        old = st.get("started:" + name)
        if old and started and old != started:
            add_event(db, now, "container_start", {"name": name, "started": started})
    was_ok = st.get("awg_ok", "1") == "1"
    if was_ok != host["awg_ok"]:
        add_event(db, now, "awg_ok" if host["awg_ok"] else "awg_unavailable")


def _host_counter_delta(st, name, cur):
    """(прирост rx, прирост tx) счётчика хоста; cur = (эпоха, rx, tx) или None."""
    if cur is None:
        return 0, 0
    epoch, rx, tx = cur
    same = st.get(name + "_epoch") == epoch
    prev_rx, prev_tx = st.get(name + "_rx"), st.get(name + "_tx")
    return (counter_delta(None if prev_rx is None else int(prev_rx), rx, same),
            counter_delta(None if prev_tx is None else int(prev_tx), tx, same))


def _cpu_pct(st, host):
    """Загрузка CPU, % за интервал с прошлого замера; None в первом замере загрузки."""
    if st.get("boot_id") != host["boot_id"] or "cpu_total" not in st:
        return None
    busy = host["cpu"][0] - int(st["cpu_busy"])
    total = host["cpu"][1] - int(st["cpu_total"])
    return 100.0 * busy / total if total > 0 else None


def _add_host_hour(db, hour, host, cpu, deltas):
    values = {
        "cpu_n": 0 if cpu is None else 1, "cpu_sum": cpu or 0.0, "cpu_max": cpu or 0.0,
        "mem_max": host["mem_used"], "mem_total": host["mem_total"], "load_max": host["load1"],
        "disk_pct": host["disk_pct"], "conntrack_max": host["conntrack"] or 0,
        "awg_miss": 0 if host["awg_ok"] else 1,
    }
    for name in HOST_COUNTERS:
        values[name + "_rx"], values[name + "_tx"] = deltas[name]
    db.execute(_HOST_UPSERT, [hour] + [values[col] for col in _HOST_COLS])


def _host_state(now, host):
    st = {"ts": now, "boot_id": host["boot_id"], "cpu_busy": host["cpu"][0],
          "cpu_total": host["cpu"][1], "awg_ok": "1" if host["awg_ok"] else "0"}
    for name, cur in host["counters"].items():
        if cur is not None:
            st[name + "_epoch"], st[name + "_rx"], st[name + "_tx"] = cur
    for name, started in host["started"].items():
        if started:
            st["started:" + name] = started
    return st


def purge_old(db, now, days=RETENTION_DAYS):
    """Удалить часовые строки и события старше `days` суток."""
    edge = int(now) - days * DAY
    db.execute("DELETE FROM peer_hourly WHERE hour_utc < ?", (edge,))
    db.execute("DELETE FROM host_hourly WHERE hour_utc < ?", (edge,))
    db.execute("DELETE FROM events WHERE ts < ?", (edge,))
