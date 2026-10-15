"""OBS-1, задача 5: sources/probes.py — пробы сети и монтирований.

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, задача 5.
Ни один настоящий процесс и ни один сокет не используется: Popen и run подменяются
параметрами интерфейса, /proc/net/tcp — файл в tmp_path. Работает на Windows и Linux.
"""
from blackbox.sources.probes import (
    MountProbe, probe_dns, probe_gateway, probe_tunnel, probes_event,
)

PROBE_TIMEOUT_S = 5

# Адреса VPS проекта и они же — как их печатает /proc/net/tcp: 32-битный адрес
# в little-endian, порт — 4 hex-цифры (22 = "0016", 443 = "01BB"),
# состояние ESTABLISHED = "01", SYN_SENT = "02".
VPS_PRIMARY = "95.163.176.103"
VPS_OLD = "193.8.215.130"
VPS_PRIMARY_HEX = "67B0A35F"
VPS_OLD_HEX = "82D708C1"

TCP_HEADER = (
    "  sl  local_address rem_address   st tx_queue rx_queue "
    "tr tm->when retrnsmt   uid  timeout inode"
)


# ── подставные процесс и run ─────────────────────────────────────────────────


class _FakeProcess(object):
    """Подставной процесс Popen.

    poll() отдаёт по одному коду из replies: None — «ещё жив», число — код
    возврата. Когда очередь исчерпана, состояние больше не меняется.
    """

    def __init__(self, replies):
        self.replies = list(replies)
        self.returncode = None
        self.killed = False

    def poll(self):
        if self.replies:
            code = self.replies.pop(0)
            if code is not None:
                self.returncode = code
        return self.returncode

    def wait(self, timeout=None):
        while self.replies:
            code = self.replies.pop(0)
            if code is not None:
                self.returncode = code
                break
        return self.returncode

    def kill(self):
        self.killed = True

    def terminate(self):
        self.killed = True


class _FakePopen(object):
    """Подставной subprocess.Popen: помнит команды, каждому запуску — свежие replies."""

    def __init__(self, replies=(None,)):
        self.template = list(replies)
        self.calls = []
        self.processes = []

    def __call__(self, args, **kwargs):
        if isinstance(args, str):
            args = args.split()
        self.calls.append([str(a) for a in args])
        process = _FakeProcess(self.template)
        self.processes.append(process)
        return process


class _FakeCompleted(object):
    """Ответ как у subprocess.CompletedProcess."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun(object):
    """Подставной subprocess.run: помнит команды, отдаёт заданный код возврата."""

    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout
        self.calls = []

    def __call__(self, args, **kwargs):
        if isinstance(args, str):
            args = args.split()
        self.calls.append([str(a) for a in args])
        return _FakeCompleted(self.returncode, self.stdout)


# ── MountProbe ───────────────────────────────────────────────────────────────


def test_mount_probe_single_flight(tmp_path):
    """Фокус ревью №1: зависший процесс — одна проба, одно событие, следующих нет."""
    path = str(tmp_path / "mnt-hdd2tb")
    popen = _FakePopen(replies=[None])  # процесс не завершается никогда
    probe = MountProbe(path, timeout_s=PROBE_TIMEOUT_S, popen=popen)
    events = []
    for i in range(10):
        event = probe.poll(1000 + i * 5)
        if event is not None:
            events.append(event)
    assert len(popen.calls) == 1
    assert [e["kind"] for e in events] == ["mount_hung"]
    assert events[0]["subject"] == path
    assert events[0]["since"] == 1000


def test_mount_probe_runs_timeout_stat_f(tmp_path):
    path = str(tmp_path / "mnt-hdd2tb")
    popen = _FakePopen(replies=[0])
    probe = MountProbe(path, timeout_s=PROBE_TIMEOUT_S, popen=popen)
    probe.poll(4000)
    parts = popen.calls[0]
    assert parts[0].endswith("timeout")
    assert parts[1] == str(PROBE_TIMEOUT_S)
    assert parts[2:4] == ["stat", "-f"]
    assert parts[4] == path


def test_mount_probe_reports_error_on_nonzero_exit(tmp_path):
    path = str(tmp_path / "mnt-hdd2tb")
    popen = _FakePopen(replies=[1])  # timeout stat -f вернул код 1
    probe = MountProbe(path, timeout_s=PROBE_TIMEOUT_S, popen=popen)
    results = [probe.poll(2000), probe.poll(2001)]
    kinds = [e["kind"] for e in results if e is not None]
    assert kinds and kinds[0] == "mount_error"


def test_mount_probe_quiet_on_success_and_probes_again(tmp_path):
    path = str(tmp_path / "mnt-hdd2tb")
    popen = _FakePopen(replies=[0])  # каждая проба отвечает сразу кодом 0
    probe = MountProbe(path, timeout_s=PROBE_TIMEOUT_S, popen=popen)
    results = [probe.poll(3000 + i) for i in range(4)]
    assert results == [None, None, None, None]
    assert len(popen.calls) >= 2  # предыдущая завершилась — следующая разрешена


def test_mount_probe_recovers_after_hang(tmp_path):
    path = str(tmp_path / "mnt-hdd2tb")
    popen = _FakePopen(replies=[None, None, None, None, 0])  # завис, затем ответил 0
    probe = MountProbe(path, timeout_s=PROBE_TIMEOUT_S, popen=popen)
    kinds = []
    for i in range(8):
        event = probe.poll(1000 + i * 5)
        if event is not None:
            kinds.append(event["kind"])
    assert kinds == ["mount_hung", "mount_recovered"]


# ── probe_gateway ────────────────────────────────────────────────────────────


def test_probe_gateway_true_when_ping_succeeds():
    run = _FakeRun(returncode=0)
    assert probe_gateway(run) is True
    assert any(part.endswith("ping") for call in run.calls for part in call)


def test_probe_gateway_false_when_ping_fails():
    run = _FakeRun(returncode=2)
    assert probe_gateway(run) is False


# ── probe_tunnel ─────────────────────────────────────────────────────────────


def _tcp_line(remote_addr_hex, remote_port_hex, state):
    return "   0: 0100007F:8AE6 %s:%s %s 00000000:00000000 02:00000000  0 0 1" % (
        remote_addr_hex, remote_port_hex, state)


def _proc_root_with_tcp(tmp_path, lines):
    net = tmp_path / "proc" / "net"
    net.mkdir(parents=True)
    (net / "tcp").write_text(
        TCP_HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return str(tmp_path / "proc")


def test_probe_tunnel_true_on_established_to_vps_22(tmp_path):
    proc_root = _proc_root_with_tcp(tmp_path, [
        _tcp_line(VPS_PRIMARY_HEX, "0016", "01"),  # 95.163.176.103:22, ESTABLISHED
    ])
    assert probe_tunnel(proc_root, (VPS_PRIMARY,)) is True


def test_probe_tunnel_false_without_established_to_vps_22(tmp_path):
    proc_root = _proc_root_with_tcp(tmp_path, [
        _tcp_line(VPS_PRIMARY_HEX, "01BB", "01"),  # тот же адрес, но порт 443
        _tcp_line(VPS_PRIMARY_HEX, "0016", "02"),  # порт 22, но SYN_SENT
        _tcp_line("0100007F", "0016", "01"),       # 127.0.0.1:22 — не адрес VPS
    ])
    assert probe_tunnel(proc_root, (VPS_PRIMARY,)) is False


def test_probe_tunnel_matches_any_vps_address(tmp_path):
    proc_root = _proc_root_with_tcp(tmp_path, [
        _tcp_line(VPS_OLD_HEX, "0016", "01"),      # 193.8.215.130:22, ESTABLISHED
    ])
    assert probe_tunnel(proc_root, (VPS_PRIMARY, VPS_OLD)) is True


# ── probes_event ─────────────────────────────────────────────────────────────


def _probe_state(**changed):
    state = {"gateway": True, "dns": True, "tunnel": True, "tg_proxy": True}
    state.update(changed)
    return state


def test_probes_event_no_change_is_empty():
    prev = _probe_state()
    assert probes_event(_probe_state(), prev) == []


def test_probes_event_dns_down_is_one_warn_event():
    prev = _probe_state()
    events = probes_event(_probe_state(dns=False), prev)
    assert len(events) == 1
    assert events[0]["kind"] == "dns_down"
    assert events[0]["severity"] == "warn"
    assert events[0]["subject"] == "dns"


def test_probes_event_any_changed_probe_gives_event():
    prev = _probe_state()
    events = probes_event(_probe_state(tunnel=False), prev)
    assert len(events) == 1


# ── probes_event: контракт event несёт ts/source (круг ревью 1, R7) ─────────


def test_probes_event_carries_ts_and_source():
    prev = _probe_state()
    events = probes_event(_probe_state(dns=False), prev, now=1791861274)
    assert len(events) == 1
    assert events[0]["ts"] == 1791861274
    assert events[0]["source"] == "probe"


# ── probe_dns: проба в дочернем процессе (круг ревью 1, R8) ──────────────────


def test_probe_dns_true_when_getent_succeeds():
    run = _FakeRun(returncode=0)
    assert probe_dns(run=run) is True
    cmd = run.calls[-1]
    assert any(part.endswith("timeout") for part in cmd)
    assert "getent" in cmd


def test_probe_dns_false_when_getent_fails():
    run = _FakeRun(returncode=1)
    assert probe_dns(run=run) is False
