"""Сборщик «чёрного ящика» (OBS-1, задача 7, спецификация §4.1 и §5.4).

Оркестрация: расписание циклов, секундный замер, процессы, heartbeat, журналы,
пробы, минутная сводка, предохранитель SSD и смена суток UTC. Всё остальное
вынесено и вызывается через делегирование:

- `collector_sources.DefaultSources` — настоящие модули задач 2–6;
- `collector_storage.Storage` — режим SSD/запас, запись, кольцо, перенос;
- `collector_events` — маскирование, хвосты и поток событий Docker.

Один процесс, один главный поток: все SQLite-хранилища, каталог, дневные базы
и курсоры принадлежат ТОЛЬКО ему. Поток есть ровно один — производитель
событий Docker (`collector_events.EventPump`): ограниченная очередь, счётчик
отброшенных, переподключение через `stop.wait(5)`; ни SQLite, ни файлов там нет.

Расписание (R3): первое срабатывание периодического цикла — ровно через
интервал после старта; fast идёт первым в каждой итерации и срабатывает
каждый тик. Частоты — fast 1 с, procs 60 с (10 с при аномалии), heartbeat
10 с, logs/probes/rollup 60 с, journal 300 с, guard 3600 с, сброс 10 с.

Python 3.6 (хост Jetson): только стандартная библиотека, без f-строк с `=`,
без `dataclasses`, без `:=`.
"""
import json
import os
import signal
import threading
import time
from os.path import ismount

from blackbox.collector_events import (LOG_READ_MAX_BYTES, EventPump,
                                       _event_producer, attach_tail,
                                       collector_event, container_id,
                                       docker_event, json_log_path,
                                       normalize_event, redact_proc)
# Публичный API пакета (тесты и выкат) сохраняется через реэкспорт.
from blackbox.collector_sources import (PROBE_TCP_TIMEOUT, TG_PROXY_HOST,
                                        TG_PROXY_PORT, DefaultSources, _HZ)
from blackbox.collector_storage import Storage
from blackbox.config import load_config
from blackbox.sources.docker_api import DockerClient
from blackbox.sources.probes import MountProbe
from blackbox.store import close_day, prune_hot, write_heartbeat

#: Частоты циклов (секунды) — раздел «Общие ограничения» плана.
FAST_S = 1
PROCS_S = 60
PROCS_ANOMALY_S = 10
HEARTBEAT_S = 10
HEARTBEAT_FALLBACK_S = 60
LOGS_S = 60
JOURNAL_S = 300
PROBES_S = 60
ROLLUP_S = 60
GUARD_S = 3600
FLUSH_S = 10
#: Предел сэмплов в минутной сводке (60 с × 1 Гц с запасом).
MINUTE_SAMPLE_CAP = 600
#: Ключи питания для метки «жив» (последний замер).
POWER_KEYS = ("vin_mv", "vin_ma", "cpu_mw", "gpu_mw")
#: Периодические циклы, чей срок считается от времени старта (R3).
_PERIODIC = ("procs", "heartbeat", "logs", "journal", "probes", "rollup", "guard")
#: Признак «источник отказал» — отличается от допустимого `None`/пустоты.
_FAIL = object()


def _guard(call, default=None):
    """Вызов источника: исключение — значение по умолчанию (сборщик жив)."""
    try:
        return call()
    except Exception:
        return default


def _probe(fn):
    """Результат пробы; исключение источника — «проба не прошла»."""
    return bool(_guard(fn, False))


def _read_boot_id(proc_root):
    """boot_id текущей загрузки из `proc_root` или `None` (не бросает)."""
    path = os.path.join(proc_root, "sys", "kernel", "random", "boot_id")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return None


_MINUTE_KEYS = ("vin_mv", "cpu_pct", "mem_avail_mb", "swap_mb", "t_cpu")


def _minute_row(ts, samples, disk_totals, health):
    """Минутная сводка: min/avg/max ключевых величин и суммы дисков."""
    row = {"ts": ts, "count": len(samples)}
    for key in _MINUTE_KEYS:
        values = [sample.get(key) for sample in samples
                  if isinstance(sample.get(key), (int, float))]
        row[key + "_min"] = min(values) if values else None
        row[key + "_max"] = max(values) if values else None
        row[key + "_avg"] = round(sum(values) / len(values), 2) if values else None
    row["disk_rios"] = disk_totals[0]
    row["disk_wios"] = disk_totals[1]
    if health:
        row["health"] = dict(health)
    return row


class Collector(object):
    """Расписание циклов; запись и перенос делегированы `Storage`."""

    def __init__(self, cfg, clock=time.time, sleep=time.sleep, sources=None,
                 stop=None):
        self.cfg = cfg
        self._clock = clock
        self._sleep = sleep
        self._stop = stop
        self._start = float(clock())
        self._last = dict((name, self._start) for name in _PERIODIC)
        self._last_flush = self._start
        self._boot_id = _read_boot_id(cfg.proc_root)
        self._fast = {"prev_cpu": None, "prev_sample": None, "power": {},
                      "anomaly": False, "d_count": 0}
        self._procs = {"raw": None, "ts": None}
        self._roll = {"samples": [], "disk": {}, "rio": 0, "wio": 0,
                      "health": {}}
        self._aux = {"logs": {}, "journal": None, "ids": {}, "probe_prev": {}}
        self.sources = (sources if sources is not None
                        else DefaultSources(cfg, log_state=self._aux["logs"]))
        self.store = Storage(cfg, self._start, ismount=ismount,
                             closer=close_day, log_state=self._aux["logs"])
        self._pump = EventPump(self.sources, clock)

    # ── расписание ──

    def _stopped(self):
        """Предикат завершения: threading.Event, функция или ничего."""
        stop = self._stop
        if stop is None:
            return self._pump.shutdown.is_set()
        if callable(getattr(stop, "is_set", None)):
            return bool(stop.is_set())
        return bool(stop())

    def _due(self, name, now, interval):
        """True не чаще `interval` секунд; первое срабатывание — старт + интервал."""
        if now - self._last[name] < interval:
            return False
        self._last[name] = now
        return True

    # ── fast: замер и аномалия ──

    def tick_fast(self, now):
        """Секундный замер: читается всегда, пишется только в режиме SSD."""
        result = _guard(lambda: self.sources.read_fast_sample(
            self.cfg, self._fast["prev_cpu"], int(now)), _FAIL)
        if result is _FAIL:
            return
        sample, disks, self._fast["prev_cpu"] = result
        previous = self._fast["prev_sample"]
        self._fast["prev_sample"] = sample
        self._fast["power"] = dict((key, sample.get(key)) for key in POWER_KEYS)
        self._note_sample(sample, disks)
        self._fast["anomaly"] = bool(_guard(lambda: self.sources.is_anomaly(
            sample, previous, self._fast["d_count"], self.cfg), False))
        self.store.add_samples([sample], disks)

    def _note_sample(self, sample, disks):
        """Копит замер и считает НЕОТРИЦАТЕЛЬНЫЕ приросты счётчиков дисков.

        Счётчики ядра кумулятивны: сумма «как есть» каждую секунду раздула бы
        минутную сводку. Первый замер диска и сброс счётчика дают 0, исчезнувший
        диск забывается (иначе его счётчики не с чем сравнивать).
        """
        roll = self._roll
        roll["samples"].append(sample)
        if len(roll["samples"]) > MINUTE_SAMPLE_CAP:
            del roll["samples"][:len(roll["samples"]) - MINUTE_SAMPLE_CAP]
        seen = set()
        for disk in disks or ():
            disk_id, rios, wios = disk[1], disk[2], disk[3]
            seen.add(disk_id)
            previous = roll["disk"].get(disk_id)
            roll["disk"][disk_id] = (rios, wios)
            if previous is None:
                continue
            if rios >= previous[0]:
                roll["rio"] += rios - previous[0]
            if wios >= previous[1]:
                roll["wio"] += wios - previous[1]
        for disk_id in list(roll["disk"]):
            if disk_id not in seen:
                del roll["disk"][disk_id]

    # ── процессы ──

    def tick_procs(self, now):
        """Снимок процессов: 60 с, при аномалии — 10 с (только SSD)."""
        interval = PROCS_ANOMALY_S if self._fast["anomaly"] else PROCS_S
        if not self._due("procs", now, interval) or self.store.mode != "ssd":
            return
        previous = self._procs["ts"]
        dt_s = None if previous is None else now - previous
        raw = _guard(lambda: self.sources.read_procs(self.cfg.proc_root, None),
                     _FAIL)
        if raw is _FAIL:
            return
        rows = _guard(lambda: self.sources.snapshot(
            self._procs["raw"], raw, dt_s, _HZ, int(now)), _FAIL)
        if rows is _FAIL:
            return
        self._procs["raw"] = raw
        self._procs["ts"] = now
        rows = [redact_proc(row, self.cfg) for row in rows]
        self._fast["d_count"] = sum(1 for row in rows
                                    if row.get("state") == "D")
        self.store.add_procs(rows)

    # ── heartbeat ──

    def tick_heartbeat(self, now):
        """Метка «жив»: 10 с, в запасном режиме — 60 с (R10: fsync-отказ — событие)."""
        interval = (HEARTBEAT_FALLBACK_S if self.store.mode == "fallback"
                    else HEARTBEAT_S)
        if not self._due("heartbeat", now, interval):
            return
        path = self.store.heartbeat_path()
        durable = _guard(lambda: write_heartbeat(
            path, self._boot_id, int(now), dict(self._fast["power"])), _FAIL)
        if durable is _FAIL:
            self._heartbeat_failed(now)
            return
        if not durable:
            self.store.buffer_event(collector_event(
                now, "heartbeat_not_durable", "warn", {"path": path}))
        self.store.enforce_cap()

    def _heartbeat_failed(self, now):
        """heartbeat на SSD не записался — в запасной режим и одна повторная попытка."""
        self.store.switch_to_fallback(now)
        _guard(lambda: write_heartbeat(
            self.store.heartbeat_path(), self._boot_id, int(now),
            dict(self._fast["power"])), _FAIL)

    # ── журналы ──

    def tick_logs(self, now):
        """Журналы контейнеров: дочитывание, счётчики здоровья, gzip дня."""
        if self.store.mode != "ssd" or not self._due("logs", now, LOGS_S):
            return
        for container in self._containers()[:200]:
            name, cid = container.get("name"), container.get("id")
            self._aux["ids"][name] = cid
            path = json_log_path(self.cfg, cid)
            if not name or path is None:
                continue
            lines = _guard(lambda: self.sources.read_new(
                name, path, LOG_READ_MAX_BYTES), _FAIL)
            if lines is _FAIL:
                continue
            split = _guard(lambda: self.sources.split_health(lines), _FAIL)
            if split is _FAIL:
                continue
            kept, health = split
            if health:
                self._roll["health"][name] = (
                    self._roll["health"].get(name, 0) + health)
            self.store.persist_logs(name, kept, now)
        self.store.save_cursor("logs", json.dumps(self._aux["logs"],
                                                  sort_keys=True), now)

    def _containers(self):
        """Список контейнеров Docker или пусто (Docker недоступен — не падаем)."""
        return _guard(lambda: list(self.sources.containers() or []), [])

    def tick_journal(self, now):
        """Порция журнала systemd раз в 5 минут — в journal.log дня."""
        if self.store.mode != "ssd" or not self._due("journal", now, JOURNAL_S):
            return
        result = _guard(lambda: self.sources.journal_since(
            self.store.journal_cursor), _FAIL)
        if result is _FAIL:
            return
        lines, new_cursor = result
        if lines:
            self.store.append_journal(lines, now)
        if new_cursor and new_cursor != self.store.journal_cursor:
            self.store.journal_cursor = new_cursor
            self.store.save_cursor("journal", new_cursor, now)

    # ── пробы ──

    def tick_probes(self, now):
        """Пробы сети и монтирований раз в 60 с; события — только при смене."""
        if not self._due("probes", now, PROBES_S):
            return
        results = self._probe_results()
        mount_event = self._mount_event(now)
        if mount_event is not None:
            self.store.buffer_event(normalize_event(mount_event, now))
        events = _guard(lambda: self.sources.probes_event(
            results, self._aux["probe_prev"]), []) or []
        self._aux["probe_prev"] = results
        for event in events:
            self.store.buffer_event(normalize_event(event, now))

    def _probe_results(self):
        """Словарь проба -> bool; туннель только при известных адресах VPS."""
        results = {
            "gateway": _probe(self.sources.probe_gateway),
            "dns": _probe(self.sources.probe_dns),
            "tg_proxy": _probe(lambda: self.sources.probe_tcp(
                TG_PROXY_HOST, TG_PROXY_PORT, PROBE_TCP_TIMEOUT)),
        }
        if getattr(self.cfg, "vps_hosts", ()):
            results["tunnel"] = _probe(self.sources.probe_tunnel)
        return results

    def _mount_event(self, now):
        """Одна проба HDD (`MountProbe.poll(now)`), в своём процессе не читаем."""
        probe = getattr(self.sources, "mount_probe", None)
        if probe is None:
            return None
        return _guard(lambda: probe.poll(now))

    # ── сводка и предохранитель ──

    def tick_rollup(self, now):
        """Минутная сводка: min/avg/max, приросты операций дисков, здоровье."""
        if not self._due("rollup", now, ROLLUP_S):
            return
        roll = self._roll
        row = _minute_row(int(now), roll["samples"],
                          (roll["rio"], roll["wio"]), roll["health"])
        roll["samples"] = []
        roll["rio"] = 0
        roll["wio"] = 0
        roll["health"] = {}
        self.store.add_minute(row, now)

    def tick_guard(self, now):
        """Предохранитель SSD раз в час — только существующим `prune_hot`."""
        if self.store.mode != "ssd" or not self._due("guard", now, GUARD_S):
            return
        _guard(lambda: prune_hot(self.store.hot_root, self.cfg.hot_cap_bytes,
                                 self.cfg.hot_min_days))

    # ── события Docker и главный цикл ──

    def _drain_events(self, now):
        """Забирает события из очереди, маскирует, прикладывает хвосты."""
        for raw in self._pump.drain():
            event = docker_event(self.sources, raw, now)
            if event is None:
                continue
            cid = container_id(self.sources, self._aux["ids"],
                               event.get("subject"))
            attach_tail(self.sources, self.cfg, event, cid)
            self.store.buffer_event(event)
        dropped = self._pump.take_dropped()
        if dropped:
            self.store.buffer_event(collector_event(
                now, "events_dropped", "warn", {"count": dropped}))

    def _iterate(self, now):
        """Одна секунда главного цикла: fast первым, затем остальные по срокам."""
        self.store.rotate(now)
        self.tick_fast(now)
        self._drain_events(now)
        self.tick_procs(now)
        self.tick_heartbeat(now)
        self.tick_logs(now)
        self.tick_journal(now)
        self.tick_probes(now)
        self.tick_rollup(now)
        self.tick_guard(now)
        if now - self._last_flush >= FLUSH_S:
            self._last_flush = now
            self.store.flush(now)
        self.store.retry(now)

    def run(self):
        """Главный цикл до остановки; по завершении — сброс буферов."""
        self._pump.start(self._start)
        while not self._stopped():
            now = self._clock()
            self._iterate(now)
            if self._stopped():
                break
            self._sleep(FAST_S)
        self._finish(self._clock())

    def _finish(self, now):
        """Останавливает поток (ограниченный join) и сбрасывает буферы."""
        self._pump.stop()
        self.store.flush(now)
        self.store.close()


# ── точка входа пакета ──────────────────────────────────────────────────────

def run(cfg, clock=time.time, sleep=time.sleep, sources=None, stop=None):
    """Создаёт сборщик и крутит главный цикл до остановки (план задачи 7)."""
    Collector(cfg, clock=clock, sleep=sleep, sources=sources, stop=stop).run()


def main(argv=None):
    """Точка входа службы: конфигурация из файла/окружения, SIGTERM — стоп."""
    del argv
    stop = threading.Event()

    def _request_stop(_signum, _frame):
        stop.set()

    for name in ("SIGTERM", "SIGINT"):
        signum = getattr(signal, name, None)
        if signum is not None:
            _guard(lambda: signal.signal(signum, _request_stop))
    run(load_config(), stop=stop)
    return 0
