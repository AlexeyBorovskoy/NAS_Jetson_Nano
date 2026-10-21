from blackbox.collector import Collector


class _FakeTime(object):
    def __init__(self):
        self.wall = 100.0
        self.mono = 0.0
        self.sleeps = []

    def clock(self):
        return self.wall

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.wall += seconds
        self.mono += seconds


class _Pump(object):
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self, now):
        self.started = True

    def stop(self):
        self.stopped = True


class _Store(object):
    def __init__(self):
        self.flushed = False
        self.closed = False

    def flush(self, now):
        self.flushed = True

    def close(self):
        self.closed = True


def test_run_compensates_bounded_iteration_work_without_catchup_sleep():
    timer = _FakeTime()
    pump = _Pump()
    store = _Store()
    ticks = []
    collector = Collector.__new__(Collector)
    collector._start = timer.clock()
    collector._clock = timer.clock
    collector._monotonic = timer.monotonic
    collector._sleep = timer.sleep
    collector._stop = lambda: len(ticks) >= 3
    collector._pump = pump
    collector.store = store

    work = iter((1.4, 0.4, 0.4))

    def bounded_tick(now):
        ticks.append(now)
        elapsed = next(work)
        timer.wall += elapsed
        timer.mono += elapsed

    collector._iterate = bounded_tick
    collector.run()

    assert ticks == [100.0, 101.4, 102.4]
    assert len(timer.sleeps) == 2
    assert timer.sleeps[0] == 0.0
    assert abs(timer.sleeps[1] - 0.6) < 1e-9
    assert pump.started and pump.stopped
    assert store.flushed and store.closed
