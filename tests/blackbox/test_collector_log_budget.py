import collections
import types

from blackbox import collector


class _Store(object):
    mode = "ssd"

    def __init__(self):
        self.reads = []
        self.cursors = []
        self.persisted = []

    def save_cursor(self, name, value, now):
        self.cursors.append((name, value, now))

    def persist_logs(self, name, lines, now):
        self.persisted.append((name, lines, now))


class _Sources(object):
    def __init__(self, count):
        self.items = [{"name": "c%d" % i, "id": "id%d" % i}
                      for i in range(count)]
        self.container_calls = 0
        self.reads = []

    def containers(self):
        self.container_calls += 1
        return list(self.items)

    def read_new(self, name, path, limit):
        self.reads.append((name, path, limit))
        return ["line"]

    @staticmethod
    def split_health(lines):
        return lines, 0


def _collector(count, monkeypatch):
    src = _Sources(count)
    c = collector.Collector.__new__(collector.Collector)
    c.store = _Store()
    c.sources = src
    c.cfg = object()
    c._last = {"logs": 0}
    c._pending_log_containers = collections.deque()
    c._aux = {"logs": {}, "ids": {}}
    c._roll = {"health": {}}
    monkeypatch.setattr(collector, "json_log_path",
                        lambda cfg, cid: "/synthetic/" + cid)
    return c, src


def test_one_container_and_16k_budget_per_iteration(monkeypatch):
    c, src = _collector(5, monkeypatch)
    for now in (60, 61, 62):
        c.tick_logs(now)
        assert len(src.reads) == (now - 59)
        assert len(c.store.cursors) == (now - 59)
    assert [r[0] for r in src.reads] == ["c0", "c1", "c2"]
    assert all(r[2] == 16 << 10 for r in src.reads)
    assert src.container_calls == 1


def test_pending_queue_survives_due_and_drains_before_refill(monkeypatch):
    c, src = _collector(3, monkeypatch)
    c.tick_logs(60)
    c.tick_logs(61)
    c.tick_logs(120)  # due boundary does not reset the remaining queue
    assert [r[0] for r in src.reads] == ["c0", "c1", "c2"]
    assert src.container_calls == 1
    c.tick_logs(121)
    assert src.container_calls == 2
    assert len(src.reads) == 4


def test_empty_queue_waits_full_period_and_due_batch_is_bounded(monkeypatch):
    c, src = _collector(205, monkeypatch)
    c.tick_logs(60)
    assert len(src.reads) == 1
    assert len(c._pending_log_containers) == 199
    for now in range(61, 260):
        c.tick_logs(now)
    assert len(src.reads) == 200
    assert not c._pending_log_containers
    c.tick_logs(260)
    assert len(src.reads) == 201
    assert src.container_calls == 2


def test_iteration_still_reaches_fast_heartbeat_and_flush():
    calls = []
    class Store(object):
        def rotate(self, now): calls.append("rotate")
        def flush(self, now): calls.append("flush")
        def retry(self, now): calls.append("retry")
    c = types.SimpleNamespace(
        store=Store(), _last_flush=0,
        _pump=types.SimpleNamespace(drain=lambda: [], take_dropped=lambda: 0))
    for name in ("tick_fast", "_drain_events", "tick_procs", "tick_heartbeat",
                 "tick_logs", "tick_journal", "tick_probes", "tick_rollup",
                 "tick_guard"):
        setattr(c, name, lambda now, n=name: calls.append(n))
    collector.Collector._iterate(c, 10)
    assert calls == ["rotate", "tick_fast", "_drain_events", "tick_procs",
                     "tick_heartbeat", "tick_logs", "tick_journal", "tick_probes",
                     "tick_rollup", "tick_guard", "flush", "retry"]
