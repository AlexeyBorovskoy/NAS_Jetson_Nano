"""Учёт приращений и хранение (спецификация 2026-10-04 §6). Ключи фиктивные."""
import json

import pytest

import vpnmon_store as vs

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
T0 = 1_759_600_800.0  # ровно начало часа UTC
MB = 1024 ** 2


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def peer(rx, tx, hs=0, ip="10.8.1.2"):
    return {"vpn_ip": ip, "rx": rx, "tx": tx, "handshake": hs}


def hourly(db, key):
    return db.execute("SELECT hour_utc, rx, tx, peak_bps FROM peer_hourly WHERE pubkey=? "
                      "ORDER BY hour_utc", (key,)).fetchall()


def make_host(**over):
    h = {
        "boot_id": "boot-1", "btime": 1_759_555_658, "cpu": (100, 1000),
        "mem_used": 500 * MB, "mem_total": 2000 * MB, "load1": 0.1, "disk_pct": 27.0,
        "conntrack": 400,
        "counters": {"wan": ("boot-1|enp0s3", 0, 0), "awg": ("boot-1|s1", 0, 0),
                     "xray": ("boot-1|x1", 0, 0)},
        "started": {"amnezia-awg2": "s1", "amnezia-xray": "x1"}, "awg_ok": True,
    }
    h.update(over)
    return h


def host_row(db, hour):
    cur = db.execute("SELECT * FROM host_hourly WHERE hour_utc=?", (hour,))
    names = [d[0] for d in cur.description]
    row = cur.fetchone()
    return dict(zip(names, row)) if row else None


def events(db):
    return [(k, json.loads(d)) for k, d in db.execute("SELECT kind, detail FROM events ORDER BY rowid")]


@pytest.mark.parametrize("prev, cur, same, expected", [
    (None, 5, True, 0), (5, 8, True, 3), (8, 3, True, 3), (5, 8, False, 8), (0, 9, True, 9),
])
def test_counter_delta(prev, cur, same, expected):
    assert vs.counter_delta(prev, cur, same) == expected


def test_minute_rate_bounds():
    assert vs.minute_rate(600, 60) == 80.0
    assert vs.minute_rate(600, 0) is None
    assert vs.minute_rate(600, 301) is None


def test_open_db_creates_private_file(tmp_path):
    import os
    import stat
    path = tmp_path / "x.db"
    vs.open_db(str(path)).close()
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert path.exists()


def test_first_run_is_baseline(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {KEY_A: "Клиент-А"}, "e1")
    assert hourly(db, KEY_A) == []
    assert vs.get_meta(db, "monitoring_start") == str(int(T0))
    assert db.execute("SELECT name, vpn_ip FROM peers").fetchall() == [("Клиент-А", "10.8.1.2")]


def test_increment_and_peak(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(160, 65000)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 60, 60000, 60060 * 8 / 60)]


def test_reset_by_epoch_counts_current_value(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(10, 20)}, {}, "e2")
    assert hourly(db, KEY_A) == [(int(T0), 10, 20, 0.0)]


def test_counter_decrease_same_epoch_is_reset(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(50, 100)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 50, 100, 0.0)]


def test_new_peer_after_start_counts_whole_counter(db):
    vs.record_peers(db, T0, {KEY_A: peer(1, 1)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(1, 1), KEY_B: peer(7, 9)}, {}, "e1")
    assert hourly(db, KEY_B) == [(int(T0), 7, 9, 0.0)]


def test_long_gap_counts_bytes_without_peak(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {}, "e1")
    vs.record_peers(db, T0 + 600, {KEY_A: peer(0, 6000)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 0, 6000, 0.0)]


def test_clock_backwards_resets_reference(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 100)}, {}, "e1")
    vs.record_peers(db, T0 - 10, {KEY_A: peer(0, 500)}, {}, "e1")
    assert hourly(db, KEY_A) == []
    vs.record_peers(db, T0 + 50, {KEY_A: peer(0, 800)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 0, 300, 300 * 8 / 60)]


def test_removed_and_returned(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_B: peer(0, 0)}, {}, "e1")
    assert db.execute("SELECT removed_at FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == (int(T0 + 60),)
    vs.record_peers(db, T0 + 120, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    assert db.execute("SELECT removed_at FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == (None,)


def test_name_kept_when_missing_and_default_for_new(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {KEY_A: "Клиент-А"}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    rows = dict(db.execute("SELECT pubkey, name FROM peers"))
    assert rows == {KEY_A: "Клиент-А", KEY_B: "ключ BBBBBBBB"}


def test_handshake_survives_reset(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0, hs=1_759_000_000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(0, 0, hs=0)}, {}, "e2")
    assert db.execute("SELECT last_handshake FROM peers").fetchone() == (1_759_000_000,)


def test_host_first_sample_has_no_cpu(db):
    vs.record_host(db, T0, make_host())
    row = host_row(db, int(T0))
    assert (row["samples"], row["cpu_n"], row["mem_max"], row["disk_pct"]) == (1, 0, 500 * MB, 27.0)
    assert events(db) == []


def test_host_cpu_and_counters_between_samples(db):
    vs.record_host(db, T0, make_host())
    counters = {"wan": ("boot-1|enp0s3", 1000, 3000), "awg": ("boot-1|s1", 10, 20),
                "xray": ("boot-1|x1", 5, 6)}
    vs.record_host(db, T0 + 60, make_host(cpu=(200, 2000), counters=counters, conntrack=900))
    row = host_row(db, int(T0))
    assert (row["samples"], row["cpu_n"], row["cpu_sum"], row["cpu_max"]) == (2, 1, 10.0, 10.0)
    assert (row["wan_rx"], row["wan_tx"], row["awg_rx"], row["awg_tx"]) == (1000, 3000, 10, 20)
    assert (row["xray_rx"], row["xray_tx"], row["conntrack_max"]) == (5, 6, 900)


def test_boot_change_event_and_counter_reset(db):
    vs.record_host(db, T0, make_host(counters={"wan": ("boot-1|enp0s3", 9000, 9000),
                                               "awg": None, "xray": None}))
    counters = {"wan": ("boot-2|enp0s3", 100, 200), "awg": None, "xray": None}
    vs.record_host(db, T0 + 1900, make_host(boot_id="boot-2", btime=int(T0 + 1800),
                                            counters=counters,
                                            shutdown_reason="hypervisor initiated shutdown"))
    assert events(db) == [("vps_down", {"from": T0, "to": int(T0 + 1800),
                                        "reason": "hypervisor initiated shutdown"})]
    row = host_row(db, int(T0))
    assert (row["wan_rx"], row["wan_tx"], row["cpu_n"]) == (100, 200, 0)


def test_container_restart_event(db):
    vs.record_host(db, T0, make_host())
    vs.record_host(db, T0 + 60, make_host(started={"amnezia-awg2": "s2", "amnezia-xray": "x1"}))
    assert events(db) == [("container_start", {"name": "amnezia-awg2", "started": "s2"})]


def test_awg_availability_transitions(db):
    vs.record_host(db, T0, make_host())
    vs.record_host(db, T0 + 60, make_host(awg_ok=False))
    vs.record_host(db, T0 + 120, make_host(awg_ok=False))
    vs.record_host(db, T0 + 180, make_host())
    assert [k for k, _ in events(db)] == ["awg_unavailable", "awg_ok"]
    assert host_row(db, int(T0))["awg_miss"] == 2


def test_missing_counter_keeps_previous_reference(db):
    vs.record_host(db, T0, make_host(counters={"wan": None, "awg": None, "xray": ("boot-1|x1", 100, 100)}))
    vs.record_host(db, T0 + 60, make_host(counters={"wan": None, "awg": None, "xray": None}))
    vs.record_host(db, T0 + 120, make_host(counters={"wan": None, "awg": None, "xray": ("boot-1|x1", 150, 170)}))
    row = host_row(db, int(T0))
    assert (row["xray_rx"], row["xray_tx"]) == (50, 70)


def test_purge_old(db):
    old = int(T0) - 401 * vs.DAY
    db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, 1, 1, 0)", (KEY_A, old))
    db.execute("INSERT INTO host_hourly (hour_utc, samples) VALUES (?, 1)", (old,))
    vs.add_event(db, old, "vps_down", {})
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {}, "e1")
    vs.purge_old(db, T0)
    counts = [db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
              for t in ("peer_hourly", "host_hourly", "events")]
    assert counts == [0, 0, 0]
