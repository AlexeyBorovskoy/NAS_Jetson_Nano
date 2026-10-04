"""Разбор сырых данных сборщика (спецификация 2026-10-04 §5–6). Ключи фиктивные."""
import json

import pytest

import vpnmon_parse as vp

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
KEY_C = "C+/c" + "c" * 39 + "="


def test_split_sections_by_marker():
    assert vp.split_sections("a\n@@\nb\nc\n@@\n\n@@\nd", 4) == ["a", "b\nc", "", "d"]


def test_split_sections_wrong_count_raises():
    with pytest.raises(ValueError):
        vp.split_sections("a\n@@\nb", 4)


def test_parse_peers_joins_three_fields():
    allowed = "%s\t10.8.1.2/32\n%s\t(none)\n" % (KEY_A, KEY_B)
    transfer = "%s\t100\t2000\n" % KEY_A
    handshakes = "%s\t1759560000\n%s\t0\n" % (KEY_A, KEY_B)
    peers = vp.parse_peers(allowed, transfer, handshakes)
    assert peers[KEY_A] == {"vpn_ip": "10.8.1.2", "rx": 100, "tx": 2000, "handshake": 1759560000}
    assert peers[KEY_B] == {"vpn_ip": None, "rx": 0, "tx": 0, "handshake": 0}


def test_parse_peers_garbage_number_raises():
    with pytest.raises(ValueError):
        vp.parse_peers("%s\t10.8.1.2/32" % KEY_A, "%s\tx\ty" % KEY_A, "")


def test_parse_clients_table_names():
    text = json.dumps([
        {"clientId": KEY_A, "userData": {"clientName": " Клиент-А "}},
        {"clientId": KEY_B, "userData": {}},
        {"clientId": KEY_C, "userData": "не словарь"},
        "мусор",
    ])
    assert vp.parse_clients_table(text) == {KEY_A: "Клиент-А"}


@pytest.mark.parametrize("text", ["", "не json", json.dumps({"a": 1})])
def test_parse_clients_table_bad_input_raises(text):
    with pytest.raises(ValueError):
        vp.parse_clients_table(text)


def test_parse_names_conf():
    text = "# комментарий\n\nC+/ccccc = Vostro\nshort = нет\nAAAAAAAA=запасной-1\nбез равенства\n"
    assert vp.parse_names_conf(text) == [("C+/ccccc", "Vostro"), ("AAAAAAAA", "запасной-1")]


def test_resolve_names_order():
    table = {KEY_A: "Клиент-А"}
    conf = [("AAAAAAAA", "из conf"), ("C+/ccccc", "Vostro")]
    names = vp.resolve_names([KEY_A, KEY_B, KEY_C], table, conf)
    assert names == {KEY_A: "Клиент-А", KEY_B: "ключ BBBBBBBB", KEY_C: "Vostro"}


def test_resolve_names_without_table_only_conf():
    conf = [("C+/ccccc", "Vostro")]
    assert vp.resolve_names([KEY_A, KEY_C], None, conf) == {KEY_C: "Vostro"}


def test_parse_cpu_counts_iowait_as_idle():
    stat = "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 1 2 3 4\n"
    assert vp.parse_cpu(stat) == (150, 1000)


def test_parse_cpu_missing_raises():
    with pytest.raises(ValueError):
        vp.parse_cpu("intr 1\n")


def test_parse_btime():
    assert vp.parse_btime("cpu  1 1 1 1\nbtime 1759555658\n") == 1759555658


def test_parse_mem():
    text = "MemTotal:        2014208 kB\nMemFree: 1 kB\nMemAvailable:    1572864 kB\n"
    assert vp.parse_mem(text) == ((2014208 - 1572864) * 1024, 2014208 * 1024)


def test_parse_mem_missing_raises():
    with pytest.raises(ValueError):
        vp.parse_mem("MemTotal: 1 kB\n")


def test_parse_load1():
    assert vp.parse_load1("0.25 0.10 0.05 1/120 4242\n") == 0.25


NET_DEV = (
    "Inter-|   Receive                            |  Transmit\n"
    " face |bytes    packets errs drop fifo frame compressed multicast|bytes\n"
    "    lo: 10 1 0 0 0 0 0 0 10 1 0 0 0 0 0 0\n"
    "enp0s3: 24561249442 20376542 0 0 0 0 0 0 25935795702 22654577 0 0 0 0 0 0\n"
)


def test_parse_net_dev():
    assert vp.parse_net_dev(NET_DEV, "enp0s3") == (24561249442, 25935795702)
    assert vp.parse_net_dev(NET_DEV, "awg0") is None


def test_parse_default_iface():
    route = ("Iface\tDestination\tGateway\tFlags\n"
             "docker0\t000011AC\t00000000\t0001\n"
             "enp0s3\t00000000\t0102A8C0\t0003\n")
    assert vp.parse_default_iface(route) == "enp0s3"
    assert vp.parse_default_iface("Iface\tDestination\n") is None


def test_parse_inspect():
    assert vp.parse_inspect("1764|2026-10-04T05:27:49.5Z|true\n") == (1764, "2026-10-04T05:27:49.5Z", True)
    with pytest.raises(ValueError):
        vp.parse_inspect("мусор")


def test_shutdown_reason_prefers_most_specific():
    journal = "Session closed\nSystem is powering down (hypervisor initiated shutdown).\n"
    assert vp.shutdown_reason(journal) == "hypervisor initiated shutdown"
    assert vp.shutdown_reason("ничего\n") is None
