"""OBS-1 «чёрный ящик», задача 7 — сборщик (blackbox/collector.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 7».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md,
§4.1 (циклы и частоты), §5.4 (запасной каталог на SD).

Таблица «Случаи для тестов» задачи 7 — каждый пункт покрыт тестом с точными
значениями:
  «125 тиков по 1 с: 125 записей sample, 2 минутные сводки, 12 heartbeat,
   procs 2 раза» — три теста test_collector_125_ticks_*;
  «аномалия с 30-й секунды — procs каждые 10 с» — *_procs_every_10s_after_anomaly;
  «flush бросает OSError» — test_collector_switches_to_fallback_on_oserror
   (фокус ревью №2 — имя теста обязано совпадать с планом дословно);
  «SSD вернулся — режим ssd, события из запасного каталога» —
   *_returns_to_ssd_and_merges_fallback_events;
  «переход через 00:00 UTC — close_day прошлого дня ровно раз» —
   *_close_day_once_on_utc_midnight;
  «die 137 с флагом OOM — в catalog.events есть detail["tail"], маскирование» —
   *_die_event_gets_redacted_tail.
Сверх таблицы покрыты: 5-минутный цикл журнала, 60-секундный цикл журналов
контейнеров, запасной режим с самого старта (SSD не смонтирован) и часовой
предохранитель SSD (§5.3 п.7).

Допущения этих тестов — план называет только подпись
run(cfg, clock, sleep, sources, stop); форму стыков задают тесты:
  • все чтения идут через объект sources (класс FakeSources ниже), методы
    названы по интерфейсам задач 2–6; sources=None в бою собирает настоящие
    модули — в тестах всегда передан один подставной источник;
  • stop — предикат без аргументов (годится и threading.Event: есть .is_set());
    True завершает цикл; проверяется каждую итерацию;
  • по завершении цикла буферы сбрасываются в базы — иначе «125 записей»
    не увидеть в metrics.db;
  • режим записи выбирается по os.path.ismount(cfg.ssd_mount) и удаче записи;
    ismount в тестах подменяется (tmp_path — не точка монтирования ни на
    Windows, ни на Linux), «отвалившийся SSD» — это DayStore.flush, бросающий
    OSError;
  • boot_id сборщик читает из cfg.proc_root/sys/kernel/random/boot_id;
  • проба монтирований — sources.mount_probe (у заглушки молчит);
  • R3 (решение ведущего 13.10): периодический цикл срабатывает при
    now − last >= interval, где last — время старта; первое срабатывание — ровно
    через интервал; fast — каждый тик с первого; аномалия оценивается на каждом
    fast-тике, fast-тик идёт первым в итерации.

Ни одного настоящего процесса, сокета или сети: subprocess.run/Popen, MountProbe
и DockerClient подменены заглушками (падают или молчат), часы и сон — подставные,
/sys, /proc и /dev не читаются. Значения, похожие на секреты, собраны
конкатенацией — сканер секретов проекта не должен ловить литерал.
"""
import gzip
import os
import subprocess
import threading
import time

from blackbox import collector
from blackbox import store
from blackbox.collector import run
from blackbox.config import Config
from blackbox.sources import container_logs
from blackbox.sources import docker_api
from blackbox.sources import probes
from blackbox.store import Catalog, DayStore, read_heartbeat

T0 = 1791861274            # 2026-10-13 03:14:34 UTC — значение из контракта плана
DAY = "2026-10-13"         # сутки T0 по UTC
MIDNIGHT = 1791936000      # 2026-10-14 00:00:00 UTC — ближайшая смена суток
BOOT_ID = "0b9d5c72-31f4-4e8a-b6d0-9c1f4a7e2b58"
SECRET = "abc123" + "def456"     # сканер секретов: значение — только склейкой

# Ид контейнера Docker (64 шестнадцатеричных знака) — как в тестах задачи 6.
DOCKER_ID = "0f1e2d3c4b5a69788796a5b4c3d2e1f0" + "00112233445566778899aabbccddeeff"
CONTAINER = "homecloud_immich_microservices"

JOURNAL_LINE = "2026-10-13T03:19:58+0000 jetson systemd[1]: Started session.\n"
JOURNAL_CURSOR = "s=abc;i=456"
HEALTH_LINE = ('172.17.0.1 - - [13/Oct/2026:03:20:01 +0000] '
               '"GET /healthcheck HTTP/1.1" 200 15\n')
CHAT_LINE = ('172.17.0.1 - - [13/Oct/2026:03:20:05 +0000] '
             '"POST /v1/chat HTTP/1.1" 200 512\n')
TAIL_LINES = [
    '172.17.0.1 - - [13/Oct/2026:03:20:01 +0000] "GET /v1/x?token='
    + SECRET + ' HTTP/1.1" 200 7\n',
    "Killed process 4242 (python3)\n",
]


def _norm(path):
    """Путь в сравнимом виде: прямые слэши, без хвостового слэша (Windows и Linux)."""
    return str(path).replace("\\", "/").rstrip("/")


def _sample(ts, mem_avail_mb=1327):
    """Замер из контракта «Контракты данных» — ключи ровно такие."""
    return {"ts": ts, "vin_mv": 5080, "vin_ma": 1450, "cpu_mw": 1200, "gpu_mw": 40,
            "t_cpu": 630, "t_gpu": 605, "t_pmic": 500, "t_ao": 645,
            "cpu_pct": 37.5, "freq_mhz": 1479, "mem_avail_mb": mem_avail_mb,
            "swap_mb": 272, "zram_mb": 455, "load1": 1.76, "net_rx": 123456789,
            "net_tx": 98765432}


def _proc_row(ts):
    """Строка контракта «proc row» — то, что вернул бы snapshot()."""
    return {"ts": int(ts), "pid": 4242, "comm": "ntfs-3g", "owner": "host",
            "cmd": "ntfs-3g /dev/sdb1 /mnt/hdd2tb", "state": "S", "wchan": "",
            "cpu_pct": 0.0, "rss_mb": 1.0}


def _container():
    return {"id": DOCKER_ID, "name": CONTAINER, "image": "homecloud/immich:latest",
            "state": "running"}


def _raw_die_event():
    """Сырое событие Docker формы GET /events: die 137 с флагом OOM."""
    return {"Type": "container", "Action": "die", "time": T0 + 1,
            "Actor": {"ID": DOCKER_ID,
                      "Attributes": {"name": CONTAINER,
                                     "image": "homecloud/immich:latest",
                                     "exitCode": "137", "oom": "true"}}}


def _make_proc_root(tmp_path, boot_id=BOOT_ID):
    """Подставной /proc: настоящий на Windows не прочитать; boot_id — из него."""
    boot = tmp_path / "proc" / "sys" / "kernel" / "random"
    boot.mkdir(parents=True, exist_ok=True)
    (boot / "boot_id").write_text(boot_id + "\n", encoding="utf-8")
    return str(tmp_path / "proc")


def _no_subprocess(*args, **kwargs):
    raise AssertionError(
        "в тестах задачи 7 настоящие subprocess запрещены: источники подставные")


# ── подставные часы, предикат завершения и классы хранилища ──────────────────

class FakeClock(object):
    """Подставные часы: clock() отдаёт время, sleep(секунды) двигает его.

    Если цикл сборщика не завершится по stop, сон упрётся в предел и тест
    упадёт с внятной ошибкой, а не повиснет.
    """

    def __init__(self, start, max_sleeps=20000):
        self.now = float(start)
        self.max_sleeps = max_sleeps
        self.sleeps = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        if self.sleeps > self.max_sleeps:
            raise RuntimeError("цикл сборщика не завершился по stop()")
        self.now += float(seconds)


class Stop(object):
    """Предикат завершения для run(cfg, …, stop=…).

    Подходит и функции-предикату (цикл зовёт stop()), и threading.Event
    (цикл зовёт stop.is_set()). Реальный предел времени — страховка от
    зависшего цикла: тест упадёт по проверке, а не повиснет.
    """

    def __init__(self, predicate, cap_s=120.0):
        self._predicate = predicate
        self._deadline = time.monotonic() + cap_s

    def __call__(self, *args, **kwargs):
        try:
            done = self._predicate(*args, **kwargs)
        except TypeError:
            if not (args or kwargs):
                raise
            done = self._predicate()      # цикл передал аргумент — предикат его не ждёт
        return bool(done) or time.monotonic() > self._deadline

    def is_set(self):
        return self()


class _QuietMountProbe(object):
    """Заглушка MountProbe (задача 5): проба молчит, процесса не запускает.

    Подставляется и в sources.mount_probe, и вместо самого класса, потому что
    popen по умолчанию у настоящего MountProbe — живой subprocess.Popen.
    """

    def __init__(self, *args, **kwargs):
        self.polls = 0

    def poll(self, now=None):
        self.polls += 1
        return None


class _QuietDockerClient(object):
    """Заглушка DockerClient (задача 4): ни сокета, ни событий."""

    def __init__(self, *args, **kwargs):
        pass

    def containers(self):
        return []

    def events(self, since_ts=None):
        block = threading.Event()

        def gen():
            block.wait()          # потока событий нет — генератор молчит
            yield None            # недостижимо: wait() без timeout не возвращается

        return gen()


class _FlakyFlush(object):
    """Отказ записи: счётчик вызовов и флаг «SSD отвалился» (flush бросает OSError).

    Сам объект на класс DayStore не ставится — он не связался бы с экземпляром
    хранилища; make_flaky_flush() оборачивает его обычной функцией.
    """

    def __init__(self, real, fail=True):
        self.real = real
        self.fail = fail
        self.calls = 0

    def __call__(self, day_store):
        self.calls += 1
        if self.fail:
            raise OSError(5, "Input/output error")
        return self.real(day_store)


# ── подставные источники задач 2–6 ───────────────────────────────────────────

class FakeSources(object):
    """Подставные источники — единственный источник данных для сборщика.

    Методы названы по интерфейсам плана: read_fast_sample (задача 2);
    read_procs / snapshot / is_anomaly (задача 6); containers / events /
    event_from_docker / read_new / split_health / tail_lines (задача 4);
    journal_since и пробы (задача 5). Вызовы считаются, данные записываются.
    """

    def __init__(self, start=T0, anomaly_from=None, containers=(),
                 new_log_lines=(), journal_lines=(JOURNAL_LINE,),
                 journal_cursor=JOURNAL_CURSOR, tail_lines=(), docker_events=()):
        self.start = float(start)
        self.anomaly_from = anomaly_from
        self.container_list = list(containers)
        self.log_lines = list(new_log_lines)
        self.journal_lines = list(journal_lines)
        self.journal_cursor = journal_cursor
        self.tail = list(tail_lines)
        self.docker_events = list(docker_events)
        self.on_sample = None

        self.fast_calls = 0
        self.sample_ts = []
        self.read_procs_calls = 0
        self.snapshot_ts = []
        self.journal_cursors = []
        self.read_new_calls = []
        self.tail_calls = []
        self.tail_at_tick = None
        self.events_calls = 0

        self.mount_probe = _QuietMountProbe()
        self.event_from_docker = docker_api.event_from_docker      # чистая функция
        self.split_health = container_logs.split_health            # чистая функция
        self._block = threading.Event()

    # ── задача 2: fast-замер ──

    def read_fast_sample(self, cfg=None, prev_cpu=None, ts=None):
        self.fast_calls += 1
        ts = int(ts if ts is not None else self.start)
        self.sample_ts.append(ts)
        if self.on_sample is not None:
            self.on_sample(ts)
        anomalous = self.anomaly_from is not None and ts >= self.anomaly_from
        sample = _sample(ts, mem_avail_mb=280 if anomalous else 1327)
        disks = [(ts, "usb-JMicron_SSD-0:0", self.fast_calls, 3, 4096, 2048, 130)]
        return sample, disks, (self.fast_calls * 100, self.fast_calls * 40)

    # ── задача 6: процессы ──

    def read_procs(self, proc_root=None, container_of=None):
        self.read_procs_calls += 1
        return []

    def snapshot(self, prev_raw=None, cur_raw=None, dt_s=None, hz=None, ts=None,
                 top_n=10):
        self.snapshot_ts.append(int(ts) if ts is not None else None)
        return [_proc_row(ts if ts is not None else self.start)]

    def is_anomaly(self, sample=None, prev_sample=None, d_count=0, cfg=None):
        """Правило аномалии в миниатюре: для расписания достаточно памяти и D-state."""
        if d_count:
            return True
        mem = (sample or {}).get("mem_avail_mb")
        return mem is not None and mem < 300

    # ── задача 4: Docker ──

    def containers(self):
        return [dict(c) for c in self.container_list]

    def events(self, since_ts=None):
        """Генератор сырых событий: отдал заготовку — и замолчал навсегда.

        Реконнект не проверяется (это поведение задачи 4), поэтому поток
        сборщика после выдачи заготовок блокируется: без исключений и без
        пятисекундных пауз, которые двигали бы подставные часы.
        """
        self.events_calls += 1
        pending = list(self.docker_events)
        block = self._block

        def gen():
            while True:
                if pending:
                    yield pending.pop(0)
                else:
                    block.wait()

        return gen()

    def read_new(self, name=None, path=None, max_bytes=None):
        self.read_new_calls.append((name, path, max_bytes))
        return list(self.log_lines)

    def tail_lines(self, path=None, n=200):
        self.tail_calls.append((path, n))
        self.tail_at_tick = self.fast_calls
        return list(self.tail)

    # ── задача 5: журнал и пробы ──

    def journal_since(self, cursor=None, run=None):
        self.journal_cursors.append(cursor)
        return list(self.journal_lines), self.journal_cursor

    def probe_gateway(self, *args, **kwargs):
        return True

    def probe_dns(self, *args, **kwargs):
        return True

    def probe_tunnel(self, *args, **kwargs):
        return True

    def probe_tcp(self, *args, **kwargs):
        return True

    def probes_event(self, results=None, prev=None):
        return []


# ── обвязка теста ────────────────────────────────────────────────────────────

class Harness(object):
    """cfg, часы, подстановки и счётчики записей, общие для всех тестов задачи.

    Подменяется только то, что нельзя создать в tmp_path: точки монтирования,
    часы, процессы и сокеты. Каталоги, sqlite-файлы и gzip — настоящие.
    """

    def __init__(self, monkeypatch, tmp_path, sources=None, start=T0):
        self.monkeypatch = monkeypatch
        self.start = float(start)
        self.sources = sources if sources is not None else FakeSources(start=start)
        self.clock = FakeClock(start)
        self.flaky = None

        self.ssd = tmp_path / "ssd"
        self.fb = tmp_path / "fb"
        self.hot_root = str(self.ssd / "hot")
        self.ssd_heartbeat = str(self.ssd / "heartbeat")
        self.fb_heartbeat = str(self.fb / "heartbeat")
        self.cfg = Config(ssd_root=str(self.ssd), fallback_root=str(self.fb),
                          ssd_mount=str(tmp_path / "mnt-ssd"),
                          proc_root=_make_proc_root(tmp_path))
        self.mounted = True

        # Поток событий Docker у заглушки молчит вечно. Если реализация при
        # остановке делает join (в том числе без таймаута), не даём тесту
        # ждать дольше половины секунды: иначе прогон повиснет на молчащем потоке.
        real_join = threading.Thread.join
        monkeypatch.setattr(
            threading.Thread, "join",
            lambda thread, timeout=None: real_join(
                thread, 0.5 if timeout is None else min(timeout, 0.5)))

        monkeypatch.setattr(os.path, "ismount", self._ismount)
        monkeypatch.setattr(collector, "ismount", self._ismount, raising=False)
        monkeypatch.setattr(subprocess, "run", _no_subprocess)
        monkeypatch.setattr(subprocess, "Popen", _no_subprocess)
        monkeypatch.setattr(probes, "MountProbe", _QuietMountProbe)
        monkeypatch.setattr(collector, "MountProbe", _QuietMountProbe, raising=False)
        monkeypatch.setattr(docker_api, "DockerClient", _QuietDockerClient)
        monkeypatch.setattr(collector, "DockerClient", _QuietDockerClient,
                            raising=False)

        # Записи в хранилище (задача 3) считаем. close_day и prune_hot только
        # записываем: их дело проверяет задача 3, здесь важны вызовы сборщика.
        self.heartbeats = []
        real_heartbeat = store.write_heartbeat

        def counted_heartbeat(path, boot_id, ts, power):
            self.heartbeats.append({"path": path, "boot_id": boot_id,
                                    "ts": ts, "power": power})
            return real_heartbeat(path, boot_id, ts, power)

        self.close_days = []

        def counted_close(hot_root, day):
            self.close_days.append((_norm(hot_root), day))

        self.prunes = []

        def counted_prune(hot_root, cap_bytes, keep_days):
            self.prunes.append((_norm(hot_root), cap_bytes, keep_days))

        for module, replacement, name in (
                (store, counted_heartbeat, "write_heartbeat"),
                (collector, counted_heartbeat, "write_heartbeat"),
                (store, counted_close, "close_day"),
                (collector, counted_close, "close_day"),
                (store, counted_prune, "prune_hot"),
                (collector, counted_prune, "prune_hot")):
            monkeypatch.setattr(module, name, replacement, raising=False)

    # ── подстановки ──

    def _ismount(self, path):
        if not self.mounted:
            return False
        return _norm(path) in (_norm(self.cfg.ssd_mount), _norm(self.cfg.ssd_root))

    def make_flaky_flush(self):
        """DayStore.flush, бросающий OSError, — «SSD отвалился посреди работы».

        На класс ставится обычная функция: только она связывается с экземпляром
        хранилища; флаг и счётчик живут в отдельном объекте _FlakyFlush.
        """
        flaky = _FlakyFlush(DayStore.flush)

        def flaky_flush(day_store):
            return flaky(day_store)

        self.flaky = flaky
        self.monkeypatch.setattr(DayStore, "flush", flaky_flush)
        return flaky

    # ── запуск ──

    def run_until(self, predicate, cap_s=120.0):
        run(self.cfg, clock=self.clock, sleep=self.clock.sleep,
            sources=self.sources, stop=Stop(predicate, cap_s=cap_s))

    def run_ticks(self, ticks):
        """Ровно ticks тиков: цикл завершается, когда источник позван в ticks-й раз."""
        self.run_until(lambda: self.sources.fast_calls >= ticks)

    # ── чтение того, что записал сборщик ──

    def samples(self, day=DAY):
        return self._read(DayStore.samples, day)

    def procs(self, day=DAY):
        return self._read(DayStore.procs, day)

    def _read(self, method, day):
        st = DayStore(self.hot_root, day)
        try:
            return method(st, self.start - 1, self.start + 10 ** 6)
        finally:
            st.close()

    def ssd_events(self, **kwargs):
        return self._events(str(self.ssd / "catalog.db"), **kwargs)

    def fallback_events(self, **kwargs):
        return self._events(str(self.fb / "catalog.db"), **kwargs)

    def _events(self, path, **kwargs):
        return Catalog(path).events(self.start - 60, self.start + 10 ** 6, **kwargs)


# ── строка таблицы 1: 125 тиков ──────────────────────────────────────────────

def test_collector_125_ticks_records_125_samples(monkeypatch, tmp_path):
    """Строка таблицы: 125 тиков по 1 с — 125 записей sample; по завершении цикла
    буферы сброшены в metrics.db (допущение этих тестов, см. заголовок файла)."""
    h = Harness(monkeypatch, tmp_path)
    h.run_ticks(125)

    assert h.sources.fast_calls == 125
    assert h.sources.sample_ts == [T0 + k for k in range(125)]

    rows = h.samples(DAY)
    assert [r["ts"] for r in rows] == [T0 + k for k in range(125)]
    assert rows[0]["vin_mv"] == 5080          # замер лёг в базу как отдан
    assert rows[0]["mem_avail_mb"] == 1327


def test_collector_125_ticks_minutes_and_heartbeats(monkeypatch, tmp_path):
    """Строка таблицы: 2 минутные сводки и 12 heartbeat за 125 тиков
    (R3: первое срабатывание — ровно через интервал: 10, 20, …, 120)."""
    h = Harness(monkeypatch, tmp_path)
    h.run_ticks(125)

    minutes = Catalog(str(h.ssd / "catalog.db")).minutes(T0 - 1, T0 + 1000)
    assert len(minutes) == 2

    assert [hb["ts"] for hb in h.heartbeats] == [T0 + 10 * k for k in range(1, 13)]
    assert all(_norm(hb["path"]) == _norm(h.ssd_heartbeat) for hb in h.heartbeats)
    assert all(hb["boot_id"] == BOOT_ID for hb in h.heartbeats)

    hb = read_heartbeat(h.ssd_heartbeat)
    assert hb is not None
    assert hb["ts"] == T0 + 120               # последний heartbeat — на 120-й секунде
    assert hb["power"]["vin_mv"] == 5080      # «последний замер питания»


def test_collector_125_ticks_procs_every_60s(monkeypatch, tmp_path):
    """Строка таблицы: без аномалии procs запускаются раз в 60 с — за 125 тиков
    ровно два раза; снимки доехали до procs.db."""
    h = Harness(monkeypatch, tmp_path)
    h.run_ticks(125)

    assert h.sources.snapshot_ts == [T0 + 60, T0 + 120]
    assert [r["ts"] for r in h.procs(DAY)] == [T0 + 60, T0 + 120]


# ── строка таблицы 2: аномалия ───────────────────────────────────────────────

def test_collector_procs_every_10s_after_anomaly(monkeypatch, tmp_path):
    """Строка таблицы: аномалия с 30-й секунды — procs каждые 10 с после неё.

    Аномалия видна по самому замеру (MemAvailable 280 МБ < 300), поэтому
    расписание переключается на fast-тике 30-й секунды, и по R3 первый
    аномальный снимок случается в том же тике (30 − 0 >= 10).
    """
    src = FakeSources(start=T0, anomaly_from=T0 + 30)
    h = Harness(monkeypatch, tmp_path, sources=src)
    h.run_ticks(125)

    times = src.snapshot_ts
    assert times == [T0 + 30 + 10 * k for k in range(10)]      # 30, 40, …, 120
    assert [b - a for a, b in zip(times, times[1:])] == [10] * 9


# ── строка таблицы 3: отказ записи (фокус ревью №2) ──────────────────────────

def test_collector_switches_to_fallback_on_oserror(monkeypatch, tmp_path):
    """Фокус ревью №2: SSD отвалился посреди работы — flush бросает OSError.

    Сборщик жив (исключение наружу не летит), уходит в запасной каталог: событие
    collector/ssd_write_failed — одно (это событие перехода, а не каждой попытки),
    heartbeat пишется в запасной каталог.
    """
    h = Harness(monkeypatch, tmp_path)
    flaky = h.make_flaky_flush()               # SSD «отвалился» на первом же flush
    h.run_ticks(130)

    assert flaky.calls >= 1                    # отказ действительно случился

    fails = [e for e in h.fallback_events()
             if e["source"] == "collector" and e["kind"] == "ssd_write_failed"]
    assert len(fails) == 1

    assert h.heartbeats, "heartbeat не записан ни разу"
    assert _norm(h.heartbeats[-1]["path"]) == _norm(h.fb_heartbeat)

    hb = read_heartbeat(h.fb_heartbeat)
    assert hb is not None
    assert hb["boot_id"] == BOOT_ID
    assert hb["ts"] >= T0 + 60                 # запасной режим: раз в минуту


# ── строка таблицы 4: SSD вернулся ───────────────────────────────────────────

def test_collector_returns_to_ssd_and_merges_fallback_events(monkeypatch, tmp_path):
    """Строка таблицы: SSD вернулся — режим ssd, события из запасного каталога
    перенесены в catalog.db; попытки возврата идут раз в 60 с."""
    h = Harness(monkeypatch, tmp_path)
    flaky = h.make_flaky_flush()
    heal_at = T0 + 80                          # с 80-й секунды запись снова удаётся
    h.sources.on_sample = lambda ts: setattr(flaky, "fail", ts < heal_at)
    h.run_ticks(220)

    merged = [e for e in h.ssd_events()
              if e["source"] == "collector" and e["kind"] == "ssd_write_failed"]
    assert len(merged) == 1                    # событие переехало из запасного каталога
    assert (h.ssd / "hot" / DAY / "metrics.db").exists()   # записи на SSD возобновились

    assert _norm(h.heartbeats[-1]["path"]) == _norm(h.ssd_heartbeat)
    hb = read_heartbeat(h.ssd_heartbeat)
    assert hb is not None
    assert hb["ts"] >= T0 + 120


# ── строка таблицы 5: смена суток ────────────────────────────────────────────

def test_collector_close_day_once_on_utc_midnight(monkeypatch, tmp_path):
    """Строка таблицы: переход через 00:00 UTC — close_day вызван для прошлого
    дня ровно раз; замеры нового дня пишутся в каталог нового дня."""
    h = Harness(monkeypatch, tmp_path, start=MIDNIGHT - 5)
    h.run_ticks(20)                            # 23:59:55 … 00:00:14 UTC

    assert h.close_days == [(_norm(h.hot_root), "2026-10-13")]

    rows = h.samples("2026-10-14")
    assert rows, "ни одной записи нового дня"
    assert [r["ts"] for r in rows] == list(range(MIDNIGHT, MIDNIGHT + len(rows)))


# ── строка таблицы 6: падение контейнера ─────────────────────────────────────

def test_collector_die_event_gets_redacted_tail(monkeypatch, tmp_path):
    """Строка таблицы: событие die 137 с флагом OOM — в catalog.events есть
    detail["tail"] с применённым маскированием; хвост — tail_lines(..., 200)."""
    src = FakeSources(containers=[_container()], docker_events=[_raw_die_event()],
                      tail_lines=TAIL_LINES)
    h = Harness(monkeypatch, tmp_path, sources=src)

    def tail_flushed():
        # событие обработано и прошла хотя бы одна минутная запись в базы
        if src.tail_at_tick is not None and src.fast_calls >= src.tail_at_tick + 12:
            return True
        return src.fast_calls >= 600           # поток не отдал событие — упасть, не висеть

    h.run_until(tail_flushed, cap_s=60.0)

    die = [e for e in h.ssd_events(source="docker") if e["kind"] == "die"]
    assert len(die) == 1
    event = die[0]
    assert event["subject"] == CONTAINER
    assert event["severity"] == "crit"         # код 137 — не 0 и не 143
    assert event["detail"]["exitCode"] == 137

    assert src.tail_calls and [n for (_path, n) in src.tail_calls] == [200]
    tail = event["detail"]["tail"]
    text = tail if isinstance(tail, str) else "".join(tail)
    assert "token=<скрыто>" in text
    assert SECRET not in text
    assert "Killed process 4242" in text       # содержательная строка прошла как есть


# ── сверх таблицы: журнал, журналы контейнеров, запасной старт, guard ────────

def test_collector_journal_cycle_appends_lines_and_saves_cursor(monkeypatch, tmp_path):
    """Цикл журнала (5 мин): строки — в <день>/journal.log, курсор — в catalog.db;
    первый вызов идёт без курсора."""
    h = Harness(monkeypatch, tmp_path)
    h.run_ticks(310)                           # первый цикл журнала — на 300-й секунде

    assert h.sources.journal_cursors == [None]
    text = (h.ssd / "hot" / DAY / "journal.log").read_text(encoding="utf-8")
    assert JOURNAL_LINE in text
    assert Catalog(str(h.ssd / "catalog.db")).get_cursor("journal") == JOURNAL_CURSOR


def test_collector_logs_cycle_writes_gz_keeping_health_out(monkeypatch, tmp_path):
    """Цикл журналов контейнеров (60 с): строки проверок здоровья уходят
    в счётчик минуты, в <день>/containers/<имя>.log.gz — только содержательные."""
    src = FakeSources(containers=[_container()],
                      new_log_lines=[HEALTH_LINE, CHAT_LINE])
    h = Harness(monkeypatch, tmp_path, sources=src)
    h.run_ticks(70)                            # первый цикл журналов — на 60-й секунде

    assert [name for (name, _path, _n) in src.read_new_calls] == [CONTAINER]
    path = h.ssd / "hot" / DAY / "containers" / (CONTAINER + ".log.gz")
    with gzip.open(str(path), "rt", encoding="utf-8") as fh:
        text = fh.read()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T0 + 60))
    # Preserve the exact message body and explicitly label its observation time.
    assert text == "%s collector %s(observed): %s" % (stamp, CONTAINER, CHAT_LINE)
    assert HEALTH_LINE not in text


def test_collector_fallback_mode_when_ssd_not_mounted(monkeypatch, tmp_path):
    """§5.4: SSD не смонтирован — сборщик с самого старта в запасном каталоге:
    чтение продолжается, heartbeat и минутные сводки — на SD, «горячего» нет."""
    h = Harness(monkeypatch, tmp_path)
    h.mounted = False
    h.run_ticks(130)

    assert h.sources.fast_calls == 130
    assert not (h.ssd / "hot").exists()        # секундные замеры на SSD не пишутся

    minutes = Catalog(str(h.fb / "catalog.db")).minutes(T0 - 1, T0 + 1000)
    assert len(minutes) == 2                   # сводки за 60-ю и 120-ю секунды

    assert h.heartbeats
    assert all(_norm(hb["path"]) == _norm(h.fb_heartbeat) for hb in h.heartbeats)
    assert h.heartbeats[-1]["ts"] == T0 + 120  # запасной режим: раз в минуту
    fb_hb = read_heartbeat(h.fb_heartbeat)
    assert fb_hb is not None
    assert fb_hb["boot_id"] == BOOT_ID


def test_collector_guard_prunes_hot_once_an_hour(monkeypatch, tmp_path):
    """Предохранитель SSD (§5.3 п.7, цикл 60 мин): prune_hot вызван ровно раз
    за час с (hot_root, cfg.hot_cap_bytes, cfg.hot_min_days)."""
    h = Harness(monkeypatch, tmp_path)
    h.run_ticks(3601)                          # первый цикл guard — на 3600-й секунде

    assert h.prunes == [(_norm(h.hot_root), h.cfg.hot_cap_bytes, h.cfg.hot_min_days)]
