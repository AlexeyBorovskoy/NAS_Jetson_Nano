"""Хранилище сборщика «чёрного ящика» (OBS-1, задача 7, §5.4).

`Storage` — единственный владелец SQLite-хранилищ сборщика: дневных баз
`DayStore`, каталога `Catalog`, режима записи (SSD/запас) и буфера событий.
Все обращения идут из главного потока.

Запасной каталог (`fallback_root`) стремится удерживать steady-state размер
`fallback_cap_bytes`: удаление строк в WAL-базе не уменьшает файл, поэтому
после тримминга выполняется `PRAGMA wal_checkpoint(TRUNCATE)` и `VACUUM`.
Операции SQLite, включая запись, checkpoint/VACUUM и временные файлы, могут
кратковременно превышать цель. В budget входят `-wal`, `-shm` и heartbeat.
Предел ниже `MIN_FALLBACK_CAP` невозможно соблюдать устойчиво —
тогда запись событий/минут в запас **не ведётся вовсе** (fail closed), а
heartbeat остаётся: это последний признак жизни.

Перенос накопленного из запаса на SSD — порциями, честно между событиями и
минутами (не «сначала всё одно»), возобновляемо после перезапуска и в режиме
SSD до полного опустошения. Подтверждение (`DELETE` из запаса) идёт только
после коммита в SSD-каталог; повтор после сбоя безопасен (дедупликация
событий по сигнатуре, минут — по ключу `ts`).

Python 3.6 (хост Jetson): SQLite 3.22, без f-строк с `=`, без `:=`.
"""
import os
import sqlite3
import time

from blackbox.collector_events import (collector_event, event_from_fallback,
                                       event_signature, parse_json_dict,
                                       redact_event, redact_text,
                                       serialized_size, MAX_EVENT_BYTES,
                                       EVENT_BUFFER_BYTES_MAX)
from blackbox.redact import mask_family_text
from blackbox.store import (Catalog, DayStore, append_gz_lines, close_day,
                            day_for_ts)

#: Попытка вернуться на SSD — раз в 60 с.
RETRY_SSD_S = 60
#: Перенос из запаса: пакет, предел строк за один шаг (возобновляемо).
MIGRATE_BATCH = 200
MIGRATE_STEP_MAX = 4000
#: Кольцо запаса: сколько строк удалять за один шаг.
TRIM_STEP = 50
#: Сколько раз за один `maintain` пересчитывать бюджет (оценка -> удаление).
TRIM_ROUNDS = 6
#: Запас под WAL/SHM и восстановление файла после `VACUUM`.
CAP_HEADROOM = 64 << 10
# This is a steady-state target: writes, WAL checkpoints and VACUUM may exceed it transiently.
#: Меньше этого предела запасной каталог честно не удержать — fail closed.
MIN_FALLBACK_CAP = 256 << 10
#: Предел буфера событий до сброса в базу (страховка от утечки памяти).
EVENT_BUFFER_MAX = 2000


def _ignore(call, default=None):
    """Ошибка файловой системы/SQLite при служебном действии — не смерть."""
    try:
        return call()
    except (OSError, sqlite3.Error):
        return default


def _close_quietly(obj):
    """Закрывает соединение/хранилище, не давая ему уронить сборщик."""
    if obj is not None:
        _ignore(obj.close)


def _ensure_dir(path):
    """Создаёт каталог (родителей тоже), если его ещё нет."""
    if path and not os.path.isdir(path):
        os.makedirs(path)


def _redact_journal(lines, cfg):
    """Masks secrets and conservatively masks Russian text when journal owner is unknown."""
    safe = []
    for line in lines:
        parts = line.splitlines(True) or [line]
        safe.extend(mask_family_text(redact_text("", part, cfg)) for part in parts)
    return "".join(part if part.endswith("\n") else part + "\n"
                   for part in safe)


def _file_size(path):
    """Размер файла вместе с `-wal` и `-shm` (физический размер базы)."""
    total = 0
    for suffix in ("", "-wal", "-shm"):
        try:
            total += os.path.getsize(path + suffix)
        except OSError:
            pass
    return total


def _walk_error(_error):
    raise OSError("fallback directory unavailable")


def _other_fallback_size(path):
    """Count snapshots and other SD files without following directory symlinks."""
    root = os.path.dirname(path)
    excluded = {path, path + "-wal", path + "-shm"}
    total = entries = 0
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=_walk_error):
        entries += len(dirs) + len(files)
        if entries > 4096:
            raise OSError("fallback directory entry limit")
        dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(directory, name))]
        for name in files:
            candidate = os.path.join(directory, name)
            if candidate not in excluded:
                total += os.lstat(candidate).st_size
    return total


def _day_of(ts):
    """Сутки UTC для `ts` или `None`, если время раньше 2020-01-01 (часы без RTC)."""
    try:
        return day_for_ts(int(ts))
    except ValueError:
        return None


def _observed_log_lines(name, lines, now):
    """Retain raw messages with an explicit observation time, not an event time."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    return ["%s collector %s(observed): %s" % (stamp, name, line)
            for line in lines]


def _delete_rowids(conn, table, rowids):
    """Удаляет подтверждённые строки пакета и фиксирует транзакцию."""
    placeholders = ", ".join("?" * len(rowids))
    with conn:
        conn.execute("DELETE FROM %s WHERE rowid IN (%s)" % (table, placeholders),
                     rowids)


# ── кольцо запасного каталога ────────────────────────────────────────────────

def _checkpoint(conn):
    """Переносит WAL в базу и обрезает его до нуля (место возвращается)."""
    _ignore(lambda: conn.execute("PRAGMA wal_checkpoint(TRUNCATE)"))


def _reclaim(conn):
    """Возвращает файлу базы место, занятое удалёнными строками."""
    _checkpoint(conn)
    _ignore(lambda: conn.execute("VACUUM"))
    _checkpoint(conn)


def _row_count(conn):
    """Сколько всего строк в `event` + `minute` запасного каталога."""
    row = conn.execute("SELECT (SELECT count(*) FROM event) + "
                       "(SELECT count(*) FROM minute)").fetchone()
    return int(row[0] or 0)


def _older_table(conn):
    """`event`/`minute` с самой старой строкой (при равенстве — `event`)."""
    event_ts, minute_ts = conn.execute(
        "SELECT (SELECT min(ts) FROM event), (SELECT min(ts) FROM minute)"
    ).fetchone()
    if event_ts is None and minute_ts is None:
        return None
    if event_ts is None:
        return "minute"
    if minute_ts is None:
        return "event"
    return "minute" if minute_ts < event_ts else "event"


def _delete_oldest(conn, count):
    """Удаляет `count` самых старых строк, честно чередуя таблицы."""
    deleted = 0
    while deleted < count:
        table = _older_table(conn)
        if table is None:
            break
        take = min(TRIM_STEP, count - deleted)
        with conn:
            removed = conn.execute(
                "DELETE FROM %s WHERE rowid IN (SELECT rowid FROM %s "
                "ORDER BY ts, rowid LIMIT ?)" % (table, table),
                (take,)).rowcount
        if not removed:
            break
        deleted += removed
    return deleted


def _trim_to_budget(conn, path, excess):
    """Удаляет примерно столько старых строк, сколько занимает `excess` байт."""
    total = _row_count(conn)
    if not total:
        return 0
    size = max(int(os.path.getsize(path)), 1)
    need = min(total, int(excess * total / size) + TRIM_STEP)
    return _delete_oldest(conn, need)


class FallbackRing(object):
    """Физический предел запасного каталога с переиспользованием места."""

    def __init__(self, path, cap_bytes, extra_paths=()):
        self.path = path
        self.cap = int(cap_bytes)
        self.extra = tuple(extra_paths)
        self.writable = self.cap >= MIN_FALLBACK_CAP

    def size(self):
        """Physical database size plus snapshots and other local fallback files."""
        return _file_size(self.path) + _other_fallback_size(self.path)

    def budget(self):
        """Бюджет записи: предел минус запас под служебные файлы SQLite."""
        return max(0, self.cap - CAP_HEADROOM)

    def maintain(self):
        """Триминг + возврат места; True — физический размер в бюджете."""
        if not self.writable or not os.path.isfile(self.path):
            return self.writable
        conn = None
        try:
            conn = sqlite3.connect(self.path)
            for _ in range(TRIM_ROUNDS):
                _checkpoint(conn)
                if self.size() <= self.budget():
                    break
                _trim_to_budget(conn, self.path, self.size() - self.budget())
                _reclaim(conn)
            self.writable = self.size() <= self.budget()
            return self.writable
        except (OSError, sqlite3.Error):
            self.writable = False
            return False
        finally:
            _close_quietly(conn)


# ── перенос из запасного каталога ───────────────────────────────────────────

class Migration(object):
    """Порционный честный перенос события/минуты из запаса в SSD-каталог."""

    def __init__(self, catalog, path):
        self.catalog = catalog
        self.path = path
        self.done = False

    def step(self, max_rows=MIGRATE_STEP_MAX):
        """Один ограниченный шаг; 0 — переносить больше нечего."""
        if self.done or not os.path.isfile(self.path):
            self.done = True
            return 0
        conn = None
        try:
            conn = sqlite3.connect(self.path)
            moved = self._run(conn, max_rows)
        finally:
            _close_quietly(conn)
        if moved == 0:
            self._finish()
        return moved

    def _run(self, conn, max_rows):
        """Чередует события и минуты, пока не израсходован бюджет шага."""
        moved = 0
        turn = 0
        while moved < max_rows:
            table = "event" if turn % 2 == 0 else "minute"
            count = self._batch(conn, table)
            moved += count
            if count == 0:
                other = "minute" if table == "event" else "event"
                count = self._batch(conn, other)
                moved += count
                if count == 0:
                    break
            turn += 1
        return moved

    def _batch(self, conn, table):
        """Один пакет таблицы `table`; подтверждение — только после коммита."""
        if table == "event":
            return self._events(conn)
        return self._minutes(conn)

    def _events(self, conn):
        rows = conn.execute(
            "SELECT rowid, ts, source, kind, subject, severity, detail "
            "FROM event ORDER BY rowid LIMIT ?", (MIGRATE_BATCH,)).fetchall()
        if not rows:
            return 0
        events = [event_from_fallback(row) for row in rows]
        existing = self._signatures(events)
        fresh = [event for event in events
                 if event_signature(event) not in existing]
        if fresh:
            self.catalog.add_events(fresh)      # коммит до подтверждения
        _delete_rowids(conn, "event", [row[0] for row in rows])
        return len(rows)

    def _signatures(self, events):
        """Сигнатуры уже записанных в SSD событий за диапазон пакета."""
        stamps = [event["ts"] for event in events
                  if isinstance(event.get("ts"), int)]
        if not stamps:
            return set()
        return set(event_signature(event) for event in
                   self.catalog.events(min(stamps), max(stamps)))

    def _minutes(self, conn):
        rows = conn.execute(
            "SELECT rowid, ts, data FROM minute ORDER BY ts LIMIT ?",
            (MIGRATE_BATCH,)).fetchall()
        if not rows:
            return 0
        for _rowid, ts, data in rows:
            row = parse_json_dict(data)
            row["ts"] = ts
            self.catalog.add_minute(row)        # коммит каждой минуты до ack
        _delete_rowids(conn, "minute", [row[0] for row in rows])
        return len(rows)

    def _finish(self):
        """Записи кончились: убирает опустевшую базу запаса и её спутники."""
        self.done = True
        for suffix in ("", "-wal", "-shm"):
            _ignore(lambda path=self.path + suffix: os.remove(path))


# ── режим записи и каталоги ─────────────────────────────────────────────────

class Storage(object):
    """SSD или запасной каталог: выбор режима, запись, возврат, ротация суток."""

    def __init__(self, cfg, start, ismount=None, closer=None, log_state=None):
        self.cfg = cfg
        self._ismount = ismount if ismount is not None else os.path.ismount
        self._closer = closer if closer is not None else close_day
        self.mode = "ssd" if self._ismount(cfg.ssd_mount) else "fallback"
        self.catalog = None
        self.day_store = None
        self.day = _day_of(start)
        self.hot_root = os.path.join(cfg.ssd_root, "hot")
        self.log_state = log_state if log_state is not None else {}
        self.journal_cursor = None
        self.events = []
        self.event_sizes = []
        self.event_bytes = 0
        self.event_drops = 0
        self.migration = None
        self.last_retry = float(start)
        self.ring = FallbackRing(
            self._path("fallback"), cfg.fallback_cap_bytes,
            (os.path.join(cfg.fallback_root, "heartbeat"),))
        self._open_initial(start)

    def _path(self, mode):
        """Путь `catalog.db` активного или запасного корня."""
        root = self.cfg.ssd_root if mode == "ssd" else self.cfg.fallback_root
        return os.path.join(root, "catalog.db")

    def _open_initial(self, now):
        """Открывает SSD или запасной каталог; отказ SSD — сразу запасной режим."""
        if self.mode == "ssd":
            try:
                self._open_ssd()
                return
            except (OSError, sqlite3.OperationalError):
                self.switch_to_fallback(now)
            return
        try:
            self._open_fallback(load_cursors=True)
        except (OSError, sqlite3.OperationalError):
            self.catalog = None      # SD тоже недоступен — жить без записи

    def _open_ssd(self):
        """SSD-каталог, дневное хранилище и продолжение переноса запаса."""
        _ensure_dir(self.cfg.ssd_root)
        self.catalog = Catalog(self._path("ssd"))
        if self.day is not None:
            self.day_store = DayStore(self.hot_root, self.day)
        self._load_cursors()
        path = self._path("fallback")
        self.migration = (Migration(self.catalog, path)
                          if os.path.isfile(path) else None)

    def _open_fallback(self, load_cursors):
        """Запасной каталог на SD; курсоры — только при старте в нём."""
        _ensure_dir(self.cfg.fallback_root)
        self.catalog = Catalog(self._path("fallback"))
        if load_cursors:
            self._load_cursors()

    def _load_cursors(self):
        """Курсоры журнала и журналов контейнеров — только через Catalog."""
        if self.catalog is None:
            return
        self.journal_cursor = _ignore(
            lambda: self.catalog.get_cursor("journal"))
        state = parse_json_dict(_ignore(lambda: self.catalog.get_cursor("logs")))
        self.log_state.clear()
        self.log_state.update(state)

    def switch_to_fallback(self, now):
        """Первый отказ записи: закрыть SSD-хранилища и писать на SD."""
        if self.mode == "fallback":
            return
        self.mode = "fallback"
        self.migration = None
        _close_quietly(self.day_store)
        self.day_store = None
        _close_quietly(self.catalog)
        self.catalog = None
        try:
            self._open_fallback(load_cursors=False)
        except (OSError, sqlite3.OperationalError):
            self.catalog = None
        self.last_retry = now
        self.buffer_event(collector_event(
            now, "ssd_write_failed", "warn",
            {"mounted": self._ismount(self.cfg.ssd_mount)}))

    def retry(self, now):
        """Раз в 60 с: если SSD снова пишется — вернуться и продолжить перенос."""
        if self.mode != "fallback" or now - self.last_retry < RETRY_SSD_S:
            return
        self.last_retry = now
        if self.day is None or not self._ismount(self.cfg.ssd_mount):
            return
        catalog = day_store = None
        try:
            _ensure_dir(self.cfg.ssd_root)
            catalog = Catalog(self._path("ssd"))
            day_store = DayStore(self.hot_root, self.day)
            day_store.flush()
        except (OSError, sqlite3.OperationalError):
            _close_quietly(day_store)
            _close_quietly(catalog)
            return
        old = self.catalog
        self.mode = "ssd"
        self.catalog = catalog
        self.day_store = day_store
        _close_quietly(old)
        self._load_cursors()
        path = self._path("fallback")
        self.migration = (Migration(self.catalog, path)
                          if os.path.isfile(path) else None)
        self.buffer_event(collector_event(now, "ssd_recovered", "info", {}))

    def rotate(self, now):
        """00:00 UTC: закрыть прошлый день ровно раз; текущий не закрывается."""
        day = _day_of(now)
        if day is None or day == self.day:
            return
        old, self.day = self.day, day
        if self.mode == "ssd":
            self._rotate_ssd(old, day, now)
        else:
            self._close_rotated_day(old)

    def _rotate_ssd(self, old, day, now):
        if self.day_store is not None:
            try:
                self.day_store.flush()
            except (OSError, sqlite3.OperationalError):
                self.switch_to_fallback(now)
        _close_quietly(self.day_store)
        self.day_store = None
        self._close_rotated_day(old)
        if self.mode == "ssd":
            try:
                self.day_store = DayStore(self.hot_root, day)
            except (OSError, sqlite3.OperationalError):
                self.switch_to_fallback(now)

    def _close_rotated_day(self, old):
        if old is not None and self._ismount(self.cfg.ssd_mount):
            self._close_old_day(old)

    def _close_old_day(self, day):
        """Сжимает journal.log прошлого дня; отказ SSD не роняет сборщик."""
        _ignore(lambda: self._closer(self.hot_root, day))

    def flush(self, now):
        """Сброс буферов: дневные базы, события, перенос запаса, кольцо."""
        if self.mode == "ssd" and self.day_store is not None:
            try:
                self.day_store.flush()
            except (OSError, sqlite3.OperationalError):
                self.switch_to_fallback(now)
        self._flush_events(now)
        if self.mode == "ssd" and self.migration is not None:
            try:
                self.migration.step()
            except (OSError, sqlite3.Error):
                self.switch_to_fallback(now)
        self.enforce_cap()

    def _flush_events(self, now):
        """Пишет буфер событий в активный каталог."""
        if self.event_drops:
            count, self.event_drops = self.event_drops, 0
            self.buffer_event(collector_event(
                now, "events_dropped", "warn", {"count": count}))
        if not self.events:
            return
        batch, self.events = self.events, []
        self.event_sizes, self.event_bytes = [], 0
        if self.mode == "fallback" and not self.ring.writable:
            self.event_drops += len(batch)
            return
        self._write(lambda catalog: catalog.add_events(batch), now)

    def _write(self, call, now):
        """Запись в каталог; отказ — запасной режим и одна повторная попытка."""
        try:
            if self.catalog is None:
                raise sqlite3.OperationalError("нет каталога")
            call(self.catalog)
        except (OSError, sqlite3.OperationalError):
            self.switch_to_fallback(now)
            if (self.catalog is None or
                    (self.mode == "fallback" and not self.ring.writable)):
                return
            _ignore(lambda: call(self.catalog))

    def buffer_event(self, event):
        """Маскирует событие и кладёт в буфер до ближайшего сброса."""
        clean = redact_event(event, self.cfg)
        size = serialized_size(clean)
        if size > MAX_EVENT_BYTES:
            self.event_drops += 1
            return
        while self.events and (len(self.events) >= EVENT_BUFFER_MAX or
                               self.event_bytes + size > EVENT_BUFFER_BYTES_MAX):
            self.events.pop(0)
            self.event_bytes -= self.event_sizes.pop(0)
            self.event_drops += 1
        if self.event_bytes + size > EVENT_BUFFER_BYTES_MAX:
            self.event_drops += 1
            return
        self.events.append(clean)
        self.event_sizes.append(size)
        self.event_bytes += size

    def add_samples(self, rows, disks):
        """Секундные замеры — только в режиме SSD (в запасе их нет)."""
        if self.mode == "ssd" and self.day_store is not None:
            self.day_store.add_samples(rows)
            self.day_store.add_disk_samples(list(disks))

    def add_procs(self, rows):
        """Снимок процессов — только в режиме SSD (в запасе их нет)."""
        if self.mode == "ssd" and self.day_store is not None:
            self.day_store.add_procs(rows)

    def add_minute(self, row, now):
        """Минутная сводка — в активный каталог; отказ — запасной режим."""
        if self.mode == "fallback" and not self.ring.writable:
            return
        self._write(lambda catalog: catalog.add_minute(row), now)
        self.enforce_cap()

    def save_cursor(self, name, value, now):
        """Курсор дочитывания — в активный Catalog."""
        self._write(lambda catalog: catalog.set_cursor(name, value), now)

    def persist_logs(self, name, lines, now):
        """Строки журнала контейнера — в gzip дня; отказ — запасной режим."""
        if not lines or self.mode != "ssd" or self.day is None:
            return
        path = os.path.join(self.hot_root, self.day, "containers",
                            name + ".log.gz")
        redacted = [redact_text(name, line, self.cfg) for line in lines]
        try:
            append_gz_lines(path, [line if line.endswith("\n") else line + "\n"
                                   for line in _observed_log_lines(name, redacted, now)])
        except OSError:
            self.switch_to_fallback(now)

    def append_journal(self, lines, now):
        """Порция журнала systemd — в journal.log дня, с маскированием."""
        if not lines or self.mode != "ssd" or self.day is None:
            return
        text = _redact_journal(lines, self.cfg)
        path = os.path.join(self.hot_root, self.day, "journal.log")
        _ensure_dir(os.path.dirname(path))
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(text)
        except OSError:
            self.switch_to_fallback(now)

    def heartbeat_path(self):
        """Путь метки «жив» в активном корне записи."""
        root = self.cfg.ssd_root if self.mode == "ssd" else self.cfg.fallback_root
        return os.path.join(root, "heartbeat")

    def enforce_cap(self):
        """Держит запасной каталог в пределах физического бюджета."""
        if self.mode == "fallback":
            self.ring.maintain()

    def close(self):
        """Закрывает дневные хранилища и каталог (сброс — на вызывающем)."""
        _close_quietly(self.day_store)
        _close_quietly(self.catalog)
