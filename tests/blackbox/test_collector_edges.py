"""OBS-1, задача 7 — краевые случаи сборщика: настоящие сигнатуры
DefaultSources, OperationalError → запас, маскирование команд/URL до записи
(в том числе глубже 5 уровней), приросты счётчиков дисков, ограниченная
очередь событий. Только подставные источники и часы: ни сети, ни /proc."""
import json
import queue
import sqlite3
import threading
import time
import types

from blackbox import collector
from blackbox import collector_events
from blackbox.config import Config
from blackbox.sources import container_logs, docker_api, journal, probes, procs, sysfs
from blackbox.store import Catalog, DayStore, read_heartbeat

T0 = 1791861274                 # 2026-10-13 03:14:34 UTC
SECRET = "abc123" + "def456"    # сканер секретов: значение — только склейкой
CONTAINER = "homecloud_stt"
DOCKER_ID = "a" * 64


class _Clock(object):
    def __init__(self, start=T0): self.now = float(start)
    def __call__(self): return self.now
    def sleep(self, seconds): self.now += float(seconds)


class _Recorder(object):
    def __init__(self, result=None): self.calls, self.result = [], result
    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


class _FakeLogTailer(object):
    def __init__(self, state, initial_tail_bytes=None):
        self.state, self.calls = state, []
        self.initial_tail_bytes = initial_tail_bytes
    def read_new(self, name, path, max_bytes):
        self.calls.append((name, path, max_bytes)); return []


class _EdgeSources(object):
    """Минимум методов сборщика; данные — из аргументов конструктора."""
    def __init__(self, docker_events=(), tail=(), proc_rows=(), containers=()):
        self.fast_calls = 0
        self._docker_events, self._tail = list(docker_events), list(tail)
        self._proc_rows, self._containers = list(proc_rows), list(containers)
        self.mount_probe = types.SimpleNamespace(poll=lambda now=None: None)
        self.event_from_docker = docker_api.event_from_docker
        self.split_health = container_logs.split_health
    def read_fast_sample(self, cfg=None, prev_cpu=None, ts=None):
        self.fast_calls += 1
        rios = (100, 103, 107)[min(self.fast_calls - 1, 2)]
        sample = {"ts": int(ts), "vin_mv": 5080, "vin_ma": 1000, "cpu_mw": 1,
                  "gpu_mw": 1}
        return sample, [(int(ts), "sda", rios, 5, 0, 0, 0)], (self.fast_calls, 0)
    def is_anomaly(self, sample=None, prev_sample=None, d_count=0, cfg=None): return False
    def events(self, since_ts=None):
        pending, block = list(self._docker_events), threading.Event()
        def gen():
            while pending: yield pending.pop(0)
            block.wait(); yield None
        return gen()
    def read_procs(self, proc_root=None, container_of=None): return []
    def snapshot(self, prev_raw=None, cur_raw=None, dt_s=None, hz=None, ts=None, top_n=10):
        return [dict(row, ts=int(ts)) for row in self._proc_rows]
    def containers(self): return [dict(c) for c in self._containers]
    def read_new(self, name=None, path=None, max_bytes=None): return []
    def tail_lines(self, path=None, n=200): return list(self._tail)
    def probe_gateway(self): return True
    def probe_dns(self): return True
    def probe_tcp(self, host, port, timeout=3): return True
    def probes_event(self, results=None, prev=None): return []


def _cfg(tmp_path):
    return Config(ssd_root=str(tmp_path / "ssd"), fallback_root=str(tmp_path / "fb"),
                  ssd_mount=str(tmp_path / "mnt-ssd"), proc_root=str(tmp_path / "proc"))


def _run_ticks(cfg, sources, ticks, monkeypatch):
    monkeypatch.setattr(collector, "ismount", lambda path: True)
    clock, deadline = _Clock(), time.monotonic() + 30.0
    collector.run(cfg, clock=clock, sleep=clock.sleep, sources=sources,
                  stop=lambda: sources.fast_calls >= ticks or time.monotonic() > deadline)


def test_default_sources_calls_real_signatures(monkeypatch):
    """DefaultSources зовёт модули задачами 2–6 ровно их сигнатурами."""
    cfg = Config(proc_root="P", sysfs_root="S", dev_root="D", docker_sock="sock",
                 hdd_mount="H", vps_hosts=("10.0.0.1",))
    run, mount = object(), object()
    docker = types.SimpleNamespace(events_calls=[], containers=lambda: [
        {"id": DOCKER_ID, "name": CONTAINER}])
    docker.events = lambda since_ts: (docker.events_calls.append(since_ts), iter(()))[1]
    fast, finder = _Recorder(({}, [], (1, 2))), _Recorder(lambda pid: "host")
    read_procs, snap, anomaly = _Recorder([]), _Recorder([]), _Recorder(False)
    jrnl, gateway, dns = _Recorder(([], "c")), _Recorder(True), _Recorder(True)
    tunnel, tcp, pevent, tails = _Recorder(True), _Recorder(True), _Recorder([]), _Recorder([])
    for module, name, value in (
            (sysfs, "read_fast_sample", fast), (procs, "container_of", finder),
            (procs, "read_procs", read_procs), (procs, "snapshot", snap),
            (procs, "is_anomaly", anomaly), (container_logs, "LogTailer", _FakeLogTailer),
            (container_logs, "tail_lines", tails), (journal, "journal_since", jrnl),
            (probes, "probe_gateway", gateway), (probes, "probe_dns", dns),
            (probes, "probe_tunnel", tunnel), (probes, "probe_tcp", tcp),
            (probes, "probes_event", pevent)):
        monkeypatch.setattr(module, name, value)
    src = collector.DefaultSources(cfg, run=run, docker_client=docker, mount_probe=mount)
    assert src.mount_probe is mount
    assert (src.read_fast_sample(cfg, None, 7), fast.calls) == (
        ({}, [], (1, 2)), [((cfg, None, 7), {})])
    assert (src.read_procs("P", None), finder.calls) == (
        [], [(("P", {DOCKER_ID: CONTAINER}), {})])
    assert read_procs.calls == [(("P", finder.result), {})]
    assert (src.snapshot(None, [], 60, 100, 7), snap.calls) == (
        [], [((None, [], 60, 100, 7, 10), {})])
    assert (src.is_anomaly({}, {}, 0, cfg), anomaly.calls) == (False, [(({}, {}, 0, cfg), {})])
    assert (list(src.events(123)), docker.events_calls) == ([], [123])
    src.read_new("n", "p", 10)
    assert src._tailer.state is src.log_state and src._tailer.calls == [("n", "p", 10)]
    assert (src.tail_lines("p", 200), tails.calls) == ([], [(("p", 200), {})])
    assert (src.journal_since("cur"), jrnl.calls) == (([], "c"), [(("cur", run), {})])
    assert (src.probe_gateway(), gateway.calls) == (True, [((run,), {})])
    assert (src.probe_dns(), dns.calls) == (True, [((), {"run": run})])
    assert (src.probe_tunnel(), tunnel.calls) == (True, [(("P", ("10.0.0.1",)), {})])
    assert (src.probe_tcp("h", 1080, 2), tcp.calls) == (True, [(("h", 1080, 2), {})])
    assert (src.probes_event({}, {}), pevent.calls) == ([], [(({}, {}), {})])


def test_operational_error_switches_to_fallback(monkeypatch, tmp_path):
    """sqlite3.OperationalError при записи — запасной режим, не смерть сборщика."""
    def broken_flush(self):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(DayStore, "flush", broken_flush)
    sources = _EdgeSources()
    _run_ticks(_cfg(tmp_path), sources, 72, monkeypatch)
    events = Catalog(str(tmp_path / "fb" / "catalog.db")).events(T0 - 60, T0 + 1000)
    assert len([e for e in events if (e["source"], e["kind"]) ==
                ("collector", "ssd_write_failed")]) == 1
    heartbeat = read_heartbeat(str(tmp_path / "fb" / "heartbeat"))
    assert heartbeat is not None and heartbeat["ts"] >= T0 + 60


def _proc_row(pid, cmd):
    return {"pid": pid, "comm": "x", "owner": "host", "state": "S", "wchan": "",
            "cmd": cmd, "cpu_pct": 0.0, "rss_mb": 1.0}


def test_command_and_url_secrets_redacted_before_write(monkeypatch, tmp_path):
    """Команды процессов и хвосты событий маскируются до записи в базы."""
    raw_event = {"Type": "container", "Action": "die", "time": T0 + 1, "Actor": {
        "ID": DOCKER_ID, "Attributes": {"name": CONTAINER, "exitCode": "137"}}}
    rows = [_proc_row(1, "svc --password " + SECRET + " --verbose"),
            _proc_row(2, "curl https://user:" + SECRET + "@example/x")]
    tail = ["connect https://bob:" + SECRET + "@nas.local/x\n",
            "svc --token " + SECRET + " --flag\n"]
    sources = _EdgeSources(docker_events=[raw_event], tail=tail, proc_rows=rows,
                           containers=[{"id": DOCKER_ID, "name": CONTAINER}])
    _run_ticks(_cfg(tmp_path), sources, 72, monkeypatch)
    procs_db = DayStore(str(tmp_path / "ssd" / "hot"), "2026-10-13")
    written = dict((row["pid"], row["cmd"])
                   for row in procs_db.procs(T0 - 1, T0 + 1000))
    procs_db.close()
    assert written[1] == "svc --password <скрыто>"
    assert written[2] == "curl https://<скрыто>@example/x"
    assert SECRET not in "".join(written.values())
    events = Catalog(str(tmp_path / "ssd" / "catalog.db")).events(
        T0 - 60, T0 + 1000, source="docker")
    text = "".join(events[0]["detail"]["tail"])
    assert "<скрыто>@nas.local" in text and "--token <скрыто>" in text
    assert SECRET not in text


def test_nested_secret_beyond_depth_is_replaced_whole(tmp_path):
    """Секрет глубже REDACT_DEPTH (5) не пишется: поддерево целиком <скрыто>."""
    node = {"password": "deep" + SECRET}
    for _ in range(8):
        node = {"n": node}
    event = {"ts": T0, "source": "docker", "kind": "die", "subject": None,
             "severity": "crit", "detail": node}
    text = json.dumps(collector_events.redact_event(event, _cfg(tmp_path)),
                      ensure_ascii=False)
    assert SECRET not in text and "<скрыто>" in text


def test_disk_rollup_counts_nonnegative_deltas(monkeypatch, tmp_path):
    """Счётчики диска кумулятивны: 100, 103, 107 -> в сводке 7, сброс -> 0."""
    sources = _EdgeSources()
    _run_ticks(_cfg(tmp_path), sources, 62, monkeypatch)
    minutes = Catalog(str(tmp_path / "ssd" / "catalog.db")).minutes(T0 - 1, T0 + 1000)
    assert (minutes[0]["disk_rios"], minutes[0]["disk_wios"]) == (7, 0)


def test_event_producer_bounded_queue_drops_and_counts():
    """Очередь событий ограничена: лишнее отбрасывается и считается."""
    burst = types.SimpleNamespace(events=lambda since_ts: iter(
        [{"time": T0 + index} for index in range(10)]))
    shutdown, out, dropped = threading.Event(), queue.Queue(maxsize=2), [0]
    thread = threading.Thread(target=collector._event_producer, daemon=True,
                              args=(burst, out, shutdown, [T0], dropped, lambda: T0))
    thread.start(); thread.join(1.0)
    shutdown.set(); thread.join(1.0)
    assert not thread.is_alive() and out.qsize() == 2 and dropped[0] >= 8
