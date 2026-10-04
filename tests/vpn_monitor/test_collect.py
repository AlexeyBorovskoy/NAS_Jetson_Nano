"""Сборщик: замер, транзакция, недоступность awg, безопасность исходника (§5, §8)."""
import json
import os
import re
import types

import pytest

import collect
import vpnmon_store as vs

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
T0 = 1_759_600_800.0
AWG_STARTED = "2026-10-04T05:27:49.577484916Z"
SRC_PATH = os.path.join(os.path.dirname(collect.__file__), "collect.py")


def wg_output(a_tx=2000, table=None):
    if table is None:
        table = json.dumps([{"clientId": KEY_A, "userData": {"clientName": "Клиент-А"}}])
    return "\n".join([
        KEY_A + "\t10.8.1.2/32", KEY_B + "\t10.8.1.5/32", "@@",
        "%s\t100\t%d" % (KEY_A, a_tx), KEY_B + "\t0\t0", "@@",
        KEY_A + "\t1759560000", KEY_B + "\t0", "@@", table,
    ])


def proc_files(boot="boot-1", busy=150):
    return {
        "stat": "cpu  %d 0 0 %d 0 0 0 0 0 0\nbtime 1759555658\n" % (busy, 1000 - busy),
        "sys/kernel/random/boot_id": boot + "\n",
        "net/route": "Iface\tDestination\tGateway\nenp0s3\t00000000\t0102A8C0\t0003\n",
        "net/dev": "Inter-|\n face |\nenp0s3: 5000 1 0 0 0 0 0 0 7000 1 0 0 0 0 0 0\n",
        "meminfo": "MemTotal: 2000000 kB\nMemAvailable: 1500000 kB\n",
        "loadavg": "0.10 0.05 0.01 1/100 123\n",
        "sys/net/netfilter/nf_conntrack_count": "473\n",
        "1764/net/dev": "  awg0: 1000 5 0 0 0 0 0 0 5000 9 0 0 0 0 0 0\n",
        "1800/net/dev": "  eth0: 300 3 0 0 0 0 0 0 400 4 0 0 0 0 0 0\n",
    }


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[:2] == ["docker", "inspect"]:
            return self.outputs.get(("inspect", cmd[-1]))
        if cmd[:2] == ["docker", "exec"]:
            return self.outputs.get("exec")
        if cmd[0] == "journalctl":
            return self.outputs.get("journal")
        return None


def sources(files, exec_out="default", running="true", journal=None):
    outputs = {
        ("inspect", "amnezia-awg2"): "1764|%s|%s\n" % (AWG_STARTED, running),
        ("inspect", "amnezia-xray"): "1800|2026-10-04T05:27:49.6Z|true\n",
        "exec": wg_output() if exec_out == "default" else exec_out,
        "journal": journal,
    }
    return types.SimpleNamespace(runner=FakeRunner(outputs), proc=lambda rel: files.get(rel, ""),
                                 disk=27.0, conf=[])


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def count(db, table):
    return db.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]


def kinds(db):
    return [row[0] for row in db.execute("SELECT kind FROM events ORDER BY rowid")]


def test_snapshot_parses_everything():
    awg, info, host = collect.snapshot(sources(proc_files()))
    peers, names = awg
    assert peers[KEY_A]["tx"] == 2000 and names[KEY_B] == "ключ BBBBBBBB"
    assert info == (1764, AWG_STARTED, True)
    assert host["counters"]["awg"] == ("boot-1|" + AWG_STARTED, 1000, 5000)
    assert host["counters"]["wan"] == ("boot-1|enp0s3", 5000, 7000)
    assert host["counters"]["xray"][1:] == (300, 400)
    assert (host["conntrack"], host["awg_ok"], host["disk_pct"]) == (473, True, 27.0)


def test_collect_once_records_host_and_peers(db):
    collect.collect_once(db, T0, sources(proc_files()))
    assert dict(db.execute("SELECT pubkey, name FROM peers")) == {KEY_A: "Клиент-А",
                                                                   KEY_B: "ключ BBBBBBBB"}
    assert count(db, "host_hourly") == 1
    assert vs.get_meta(db, "monitoring_start") == str(int(T0))


def test_second_sample_counts_increments(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(busy=250), exec_out=wg_output(a_tx=62000)))
    assert db.execute("SELECT tx, peak_bps FROM peer_hourly WHERE pubkey=?", (KEY_A,)).fetchone() == (60000, 8000.0)


def test_awg_unavailable_records_host_only(db):
    collect.collect_once(db, T0, sources(proc_files(), exec_out=None))
    assert count(db, "peers") == 0 and count(db, "host_hourly") == 1
    assert kinds(db) == ["awg_unavailable"]


def test_zero_peers_is_unavailable_not_mass_removal(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(), exec_out="@@\n@@\n@@\n[]"))
    assert db.execute("SELECT COUNT(*) FROM peers WHERE removed_at IS NULL").fetchone()[0] == 2
    assert kinds(db) == ["awg_unavailable"]


def test_container_not_running_skips_exec(db):
    src = sources(proc_files(), running="false")
    collect.collect_once(db, T0, src)
    assert not any(cmd[:2] == ["docker", "exec"] for cmd in src.runner.calls)
    assert kinds(db) == ["awg_unavailable"]


def test_broken_clients_table_keeps_names(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(), exec_out=wg_output(table="не json")))
    assert db.execute("SELECT name FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == ("Клиент-А",)


def test_journal_read_only_on_boot_change(db):
    first = sources(proc_files())
    collect.collect_once(db, T0, first)
    assert not any(cmd[0] == "journalctl" for cmd in first.runner.calls)
    journal = "System is powering down (hypervisor initiated shutdown).\n"
    second = sources(proc_files(boot="boot-2"), journal=journal)
    collect.collect_once(db, T0 + 1900, second)
    assert sum(cmd[0] == "journalctl" for cmd in second.runner.calls) == 1
    detail = json.loads(db.execute("SELECT detail FROM events WHERE kind='vps_down'").fetchone()[0])
    assert detail["reason"] == "hypervisor initiated shutdown"


def test_failure_inside_transaction_writes_nothing(db, monkeypatch):
    def boom(*_args):
        raise RuntimeError("сбой записи")
    monkeypatch.setattr(collect.vs, "record_peers", boom)
    with pytest.raises(RuntimeError):
        collect.collect_once(db, T0, sources(proc_files()))
    assert count(db, "host_hourly") == 0 and count(db, "host_state") == 0


def test_source_never_reads_secrets():
    src = open(SRC_PATH, encoding="utf-8").read()
    for word in ("dump", "showconf", "private"):
        assert word not in src.lower(), word


def test_docker_only_exec_and_inspect():
    src = open(SRC_PATH, encoding="utf-8").read()
    verbs = set(re.findall(r'"docker",\s*"(\w+)"', src))
    assert verbs == {"exec", "inspect"}


def test_read_script_is_constant_and_fails_closed():
    assert "%" not in collect.WG_READ_SCRIPT and "{" not in collect.WG_READ_SCRIPT
    assert collect.WG_READ_SCRIPT.startswith("set -e;")
