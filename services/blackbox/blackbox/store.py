"""Хранилище «чёрного ящика» (OBS-1, задача 3, спецификация §5.1–5.3).

`DayStore` — секундные замеры и снимки процессов одного дня (`metrics.db`,
`procs.db`, SQLite WAL). `Catalog` — минутные сводки, события, загрузки,
недельные архивы и курсоры дочитывания (`catalog.db`). `write_heartbeat`/
`read_heartbeat` — метка «жив» (временный файл + fsync + `os.replace`).
`append_gz_lines`/`close_day` — журналы контейнеров и systemd (gzip-блоки,
дневной `journal.log` -> `.xz`). `hot_size_bytes`/`prune_hot` — предохранитель
SSD (раздел 5.3, пункт 7): предел «горячего», сначала `metrics.db`, затем
`procs.db`, `containers/`/`journal.log*` и сегодняшний день — никогда.

Сутки — по UTC, время в базах — целые секунды эпохи UTC. Хост — SQLite 3.22:
никаких возможностей новее (`UPSERT ... ON CONFLICT DO UPDATE` — с 3.24),
только `INSERT OR REPLACE`/`UPDATE`. Python 3.6: только стандартная
библиотека, без f-строк с `=`, без `dataclasses`, без `:=`.
"""
import calendar
import gzip
import json
import lzma
import os
import shutil
import sqlite3
import time

#: Порог `day_for_ts`: 2020-01-01 00:00:00 UTC. Часы без RTC-батарейки могут
#: показывать 1970-й — такой замер не должен молча создать каталог в «горячем».
_DAY_FLOOR_TS = 1577836800


def day_for_ts(ts):
    """`"ГГГГ-ММ-ДД"` по UTC; `ts < 2020-01-01 UTC` -> `ValueError` (ревью №3)."""
    if ts < _DAY_FLOOR_TS:
        raise ValueError("day_for_ts: ts=%r раньше порога 2020-01-01 UTC" % (ts,))
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _open_db(path):
    """Соединение sqlite3 с `PRAGMA journal_mode=WAL` (храповик-решение)."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── DayStore: metrics.db, procs.db ──────────────────────────────────────────

_SAMPLE_COLUMNS = (
    "ts", "vin_mv", "vin_ma", "cpu_mw", "gpu_mw", "t_cpu", "t_gpu", "t_pmic",
    "t_ao", "cpu_pct", "freq_mhz", "mem_avail_mb", "swap_mb", "zram_mb",
    "load1x100", "net_rx", "net_tx",
)
_SAMPLE_INSERT = "INSERT OR REPLACE INTO sample (%s) VALUES (%s)" % (
    ", ".join(_SAMPLE_COLUMNS), ", ".join("?" * len(_SAMPLE_COLUMNS)))
_SAMPLE_SELECT = "SELECT %s FROM sample WHERE ts BETWEEN ? AND ? ORDER BY ts" % (
    ", ".join(_SAMPLE_COLUMNS))

_DISK_SAMPLE_INSERT = (
    "INSERT OR REPLACE INTO disk_sample "
    "(ts, disk_id, rios, wios, rsect, wsect, busy_ms) VALUES (?,?,?,?,?,?,?)"
)
_DISK_SAMPLE_SELECT = (
    "SELECT ts, disk_id, rios, wios, rsect, wsect, busy_ms FROM disk_sample "
    "WHERE ts BETWEEN ? AND ? ORDER BY ts"
)

_PROC_COLUMNS = ("ts", "pid", "comm", "owner", "cmd", "state", "wchan",
                  "cpu_pct", "rss_mb")
_PROC_INSERT = "INSERT OR REPLACE INTO proc_snapshot (%s) VALUES (%s)" % (
    ", ".join(_PROC_COLUMNS), ", ".join("?" * len(_PROC_COLUMNS)))
_PROC_SELECT = "SELECT %s FROM proc_snapshot WHERE ts BETWEEN ? AND ? ORDER BY ts" % (
    ", ".join(_PROC_COLUMNS))


def _sample_params(row):
    """Параметры `_SAMPLE_INSERT` из dict `sample` (`load1` -> ×100 целое)."""
    load1 = row.get("load1")
    values = dict((k, row.get(k)) for k in _SAMPLE_COLUMNS)
    values["load1x100"] = None if load1 is None else int(round(load1 * 100))
    return tuple(values[k] for k in _SAMPLE_COLUMNS)


def _sample_from_row(row):
    """Строка `sample` -> dict контракта (`load1x100` -> `load1`, /100)."""
    values = dict(zip(_SAMPLE_COLUMNS, row))
    load1x100 = values.pop("load1x100")
    values["load1"] = None if load1x100 is None else load1x100 / 100.0
    return values


def _ensure_metrics_schema(conn):
    """Таблицы `sample`/`disk_sample` в `metrics.db`, если их ещё нет."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sample ("
        "ts INTEGER PRIMARY KEY, vin_mv INTEGER, vin_ma INTEGER, "
        "cpu_mw INTEGER, gpu_mw INTEGER, t_cpu INTEGER, t_gpu INTEGER, "
        "t_pmic INTEGER, t_ao INTEGER, cpu_pct REAL, freq_mhz INTEGER, "
        "mem_avail_mb INTEGER, swap_mb INTEGER, zram_mb INTEGER, "
        "load1x100 INTEGER, net_rx INTEGER, net_tx INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS disk_sample ("
        "ts INTEGER, disk_id TEXT, rios INTEGER, wios INTEGER, "
        "rsect INTEGER, wsect INTEGER, busy_ms INTEGER, "
        "PRIMARY KEY (ts, disk_id))"
    )
    conn.commit()


def _ensure_procs_schema(conn):
    """Таблица `proc_snapshot` в `procs.db`, если её ещё нет."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS proc_snapshot ("
        "ts INTEGER, pid INTEGER, comm TEXT, owner TEXT, cmd TEXT, "
        "state TEXT, wchan TEXT, cpu_pct REAL, rss_mb REAL, "
        "PRIMARY KEY (ts, pid))"
    )
    conn.commit()


class DayStore(object):
    """SQLite-хранилище одного дня: `<hot_root>/<day>/{metrics,procs}.db`.

    `add_*` копят строки в памяти; `flush()` пишет каждый файл одной
    транзакцией (`PRAGMA journal_mode=WAL` выставлена при открытии).
    """

    def __init__(self, hot_root, day):
        self._dir = os.path.join(hot_root, day)
        if not os.path.isdir(self._dir):
            os.makedirs(self._dir)
        self._metrics = _open_db(os.path.join(self._dir, "metrics.db"))
        self._procs = _open_db(os.path.join(self._dir, "procs.db"))
        _ensure_metrics_schema(self._metrics)
        _ensure_procs_schema(self._procs)
        self._samples = []
        self._disk_samples = []
        self._proc_rows = []

    def add_samples(self, rows):
        """Копит строки контракта `sample` в памяти до `flush()`."""
        self._samples.extend(rows)

    def add_disk_samples(self, rows):
        """Копит кортежи `disk_sample` в памяти до `flush()`."""
        self._disk_samples.extend(rows)

    def add_procs(self, rows):
        """Копит строки контракта `proc row` в памяти до `flush()`."""
        self._proc_rows.extend(rows)

    def flush(self):
        """Пишет накопленное: metrics.db и procs.db — по одной транзакции."""
        if self._samples or self._disk_samples:
            self._flush_metrics()
        if self._proc_rows:
            self._flush_procs()

    def _flush_metrics(self):
        with self._metrics:
            for row in self._samples:
                self._metrics.execute(_SAMPLE_INSERT, _sample_params(row))
            for row in self._disk_samples:
                self._metrics.execute(_DISK_SAMPLE_INSERT, row)
        self._samples = []
        self._disk_samples = []

    def _flush_procs(self):
        with self._procs:
            for row in self._proc_rows:
                params = tuple(row.get(k) for k in _PROC_COLUMNS)
                self._procs.execute(_PROC_INSERT, params)
        self._proc_rows = []

    def samples(self, since, until):
        """[`sample`, ...] c `since <= ts <= until`, по возрастанию `ts`."""
        rows = self._metrics.execute(_SAMPLE_SELECT, (since, until)).fetchall()
        return [_sample_from_row(row) for row in rows]

    def disk_samples(self, since, until):
        """[(ts, disk_id, rios, wios, rsect, wsect, busy_ms), ...] по `ts`."""
        return self._metrics.execute(_DISK_SAMPLE_SELECT, (since, until)).fetchall()

    def procs(self, since, until):
        """[`proc row`, ...] c `since <= ts <= until`, по возрастанию `ts`."""
        rows = self._procs.execute(_PROC_SELECT, (since, until)).fetchall()
        return [dict(zip(_PROC_COLUMNS, row)) for row in rows]

    def close(self):
        """Закрывает оба соединения (`flush()` до закрытия — на вызывающем)."""
        self._metrics.close()
        self._procs.close()


# ── Catalog: catalog.db ──────────────────────────────────────────────────────

_BOOT_COLUMNS = ("boot_id", "start", "end", "clean", "last_heartbeat",
                  "reset_source", "pstore", "verdict", "confidence")
_BOOT_SELECT = (
    "SELECT boot_id, start, \"end\", clean, last_heartbeat, reset_source, "
    "pstore, verdict, confidence FROM boot"
)
_ARCHIVE_COLUMNS = ("week", "path", "sha256", "first_day", "last_day",
                     "created", "verified")
_ARCHIVE_SELECT = "SELECT %s FROM archive" % ", ".join(_ARCHIVE_COLUMNS)


def _event_from_row(row):
    """Строка `event` -> dict контракта (`detail` — JSON -> dict)."""
    ts, source, kind, subject, severity, detail = row
    return {"ts": ts, "source": source, "kind": kind, "subject": subject,
            "severity": severity, "detail": json.loads(detail)}


def _boot_from_row(row):
    """Строка `boot` -> dict контракта (`pstore` — JSON -> list)."""
    values = dict(zip(_BOOT_COLUMNS, row))
    values["pstore"] = json.loads(values["pstore"]) if values["pstore"] else []
    return values


def _archive_from_row(row):
    """Строка `archive` -> dict контракта (`verified` -> bool)."""
    values = dict(zip(_ARCHIVE_COLUMNS, row))
    values["verified"] = bool(values["verified"])
    return values


def _ensure_catalog_schema(conn):
    """Таблицы `event`/`minute`/`boot`/`archive`/`cursor` в `catalog.db`."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS event (ts INTEGER, source TEXT, kind TEXT, "
        "subject TEXT, severity TEXT, detail TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS minute (ts INTEGER PRIMARY KEY, data TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS boot (boot_id TEXT PRIMARY KEY, "
        "start INTEGER, \"end\" INTEGER, clean INTEGER, last_heartbeat INTEGER, "
        "reset_source TEXT, pstore TEXT, verdict TEXT, confidence TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS archive (week TEXT PRIMARY KEY, path TEXT, "
        "sha256 TEXT, first_day TEXT, last_day TEXT, created INTEGER, "
        "verified INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cursor (name TEXT PRIMARY KEY, value TEXT)"
    )
    conn.commit()


class Catalog(object):
    """SQLite-хранилище `catalog.db`: события, минуты, загрузки, архивы, курсоры."""

    def __init__(self, path):
        self._conn = _open_db(path)
        _ensure_catalog_schema(self._conn)

    def add_events(self, rows):
        """Пишет события (`detail` — dict -> JSON) одной транзакцией."""
        with self._conn:
            for row in rows:
                detail = json.dumps(row.get("detail", {}), ensure_ascii=False)
                self._conn.execute(
                    "INSERT INTO event (ts, source, kind, subject, severity, "
                    "detail) VALUES (?,?,?,?,?,?)",
                    (row["ts"], row["source"], row["kind"], row["subject"],
                     row["severity"], detail))

    def events(self, since, until, source=None, subject=None):
        """[`event`, ...] в `[since, until]`, опционально по `source`/`subject`."""
        sql = ("SELECT ts, source, kind, subject, severity, detail FROM event "
               "WHERE ts BETWEEN ? AND ?")
        params = [since, until]
        if source is not None:
            sql += " AND source = ?"
            params.append(source)
        if subject is not None:
            sql += " AND subject = ?"
            params.append(subject)
        rows = self._conn.execute(sql + " ORDER BY ts", params).fetchall()
        return [_event_from_row(row) for row in rows]

    def add_minute(self, row):
        """Пишет минутную сводку (`ts` — ключ, остальное — JSON)."""
        rest = dict(row)
        ts = rest.pop("ts")
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO minute (ts, data) VALUES (?,?)",
                (ts, json.dumps(rest, ensure_ascii=False)))

    def minutes(self, since, until):
        """[минутная сводка, ...] в `[since, until]`, по возрастанию `ts`."""
        rows = self._conn.execute(
            "SELECT ts, data FROM minute WHERE ts BETWEEN ? AND ? ORDER BY ts",
            (since, until)).fetchall()
        result = []
        for ts, data in rows:
            merged = json.loads(data)
            merged["ts"] = ts
            result.append(merged)
        return result

    def upsert_boot(self, row):
        """Вставляет/обновляет строку `boot` (merge: прежние поля + `row`)."""
        existing = self.get_boot(row["boot_id"])
        merged = {} if existing is None else existing
        merged.update(row)
        self._write_boot(merged)

    def _write_boot(self, row):
        pstore = row.get("pstore")
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO boot (boot_id, start, \"end\", clean, "
                "last_heartbeat, reset_source, pstore, verdict, confidence) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (row["boot_id"], row.get("start"), row.get("end"),
                 row.get("clean"), row.get("last_heartbeat"),
                 row.get("reset_source"),
                 json.dumps(pstore if pstore is not None else []),
                 row.get("verdict"), row.get("confidence")))

    def get_boot(self, boot_id):
        """Строка `boot` по `boot_id` или `None`."""
        row = self._conn.execute(
            _BOOT_SELECT + " WHERE boot_id = ?", (boot_id,)).fetchone()
        return None if row is None else _boot_from_row(row)

    def boots(self, limit=20):
        """Загрузки, новые первыми (`start` по убыванию), не больше `limit`."""
        rows = self._conn.execute(
            _BOOT_SELECT + " ORDER BY start DESC LIMIT ?", (limit,)).fetchall()
        return [_boot_from_row(row) for row in rows]

    def get_cursor(self, name):
        """Значение курсора `name` или `None`, если такого имени ещё не было."""
        row = self._conn.execute(
            "SELECT value FROM cursor WHERE name = ?", (name,)).fetchone()
        return None if row is None else row[0]

    def set_cursor(self, name, value):
        """Сохраняет изменённое значение курсора; одинаковое не переписывает WAL."""
        row = self._conn.execute(
            "SELECT value FROM cursor WHERE name = ?", (name,)).fetchone()
        if row is not None and row[0] == value:
            return False
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO cursor (name, value) VALUES (?,?)",
                (name, value))
        return True

    def add_archive(self, row):
        """Пишет строку `archive` (одна запись на неделю, PK — `week`)."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO archive (week, path, sha256, "
                "first_day, last_day, created, verified) VALUES (?,?,?,?,?,?,?)",
                (row["week"], row["path"], row["sha256"], row["first_day"],
                 row["last_day"], row["created"], int(bool(row.get("verified")))))

    def archives(self):
        """Все строки `archive`, по неделе."""
        rows = self._conn.execute(_ARCHIVE_SELECT + " ORDER BY week").fetchall()
        return [_archive_from_row(row) for row in rows]

    def archive_for_day(self, day):
        """Архив, чей `[first_day, last_day]` содержит `day`, или `None`."""
        row = self._conn.execute(
            _ARCHIVE_SELECT + " WHERE first_day <= ? AND last_day >= ? LIMIT 1",
            (day, day)).fetchone()
        return None if row is None else _archive_from_row(row)

    def close(self):
        """Закрывает соединение `catalog.db`."""
        self._conn.close()


# ── heartbeat: временный файл + fsync + os.replace ──────────────────────────

def _fsync_dir(directory):
    """`fsync` каталога (переживает `os.replace`) -> `True`/`False` (успех).

    Круг 1 ревью: раньше `OSError` молча глушился — на Linux это прячет
    настоящие ошибки (`ENOSPC`, права). Теперь отказ возвращается вызывающей
    стороне, а не теряется; сборщик (задача 7) решает, заводить ли событие.
    На не-POSIX (Windows, тестовый хост) каталог не fsync-ится вовсе —
    `os.name != "posix"` -> `True` без попытки: это свойство платформы, не
    отказ (целевой хост — Jetson, Linux/POSIX).
    """
    if os.name != "posix":
        return True
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def write_heartbeat(path, boot_id, ts, power):
    """Пишет `{"boot_id","ts","power"}` в `path` атомарно, без `.tmp`-хвоста.

    Возвращает `True`/`False` — удался ли `fsync` каталога после
    `os.replace` (круг 1 ревью). Сам файл при этом уже записан и цел в обоих
    случаях; `False` — сигнал вызывающей стороне, не повод отбросить запись.
    """
    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        os.makedirs(directory)
    payload = json.dumps({"boot_id": boot_id, "ts": ts, "power": power},
                          ensure_ascii=False)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, path)
    return _fsync_dir(directory)


def read_heartbeat(path):
    """dict `{"boot_id","ts","power"}` или `None`: нет файла, пуст, повреждён."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return None
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


# ── журналы: gzip-блоки, дневной journal.log -> .xz ─────────────────────────

def append_gz_lines(path, lines):
    """Дописывает автономный gzip-блок с `lines` в конец `path` (создаёт файл).

    Конкатенация gzip-блоков — валидный gzip-поток: `gzip.open(...).read()`
    декодирует все блоки по порядку, без пересборки прежних байт.
    """
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    payload = "".join(lines).encode("utf-8")
    with open(path, "ab") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb") as gz:
            gz.write(payload)


def close_day(hot_root, day):
    """`<hot_root>/<day>/journal.log` -> `.xz` (через временный файл), исходник удалить."""
    day_dir = os.path.join(hot_root, day)
    src = os.path.join(day_dir, "journal.log")
    if not os.path.isfile(src):
        return
    dst = src + ".xz"
    tmp_dst = dst + ".tmp"
    with open(src, "rb") as raw_in:
        with lzma.open(tmp_dst, "wb", preset=0) as compressed:
            shutil.copyfileobj(raw_in, compressed)
    os.replace(tmp_dst, dst)
    os.remove(src)


# ── предохранитель SSD: hot_size_bytes / prune_hot ──────────────────────────

def hot_size_bytes(hot_root):
    """Сумма размеров всех файлов дерева `hot_root` (рекурсивно)."""
    total = 0
    for root, _dirs, files in os.walk(hot_root):
        for name in files:
            total += os.path.getsize(os.path.join(root, name))
    return total


def _today_name():
    """Имя сегодняшнего дня (`"ГГГГ-ММ-ДД"`, UTC) — порог безусловной защиты."""
    return time.strftime("%Y-%m-%d", time.gmtime())


def _day_age(day_name):
    """Возраст суток `day_name` (ГГГГ-ММ-ДД, UTC) от сегодняшних суток UTC."""
    today_start = int(time.time()) // 86400 * 86400
    day_start = calendar.timegm(time.strptime(day_name, "%Y-%m-%d"))
    return (today_start - day_start) // 86400


def _eligible_days(hot_root, keep_days):
    """Имена дней `hot_root` с возрастом `>= keep_days`.

    Круг 1 ревью: сегодняшний день исключён БЕЗУСЛОВНО, именем (`_today_name`),
    а не порогом возраста — иначе `keep_days <= 0` пускал его в удаление
    (возраст сегодня = 0, `0 >= 0`/`0 >= -1` истинны). Проверено ревьюером:
    `prune_hot(..., keep_days=0)` удалял `metrics.db` сегодняшнего дня.
    """
    try:
        names = os.listdir(hot_root)
    except OSError:
        return []
    today = _today_name()
    ages = {}
    for name in names:
        if name == today or not os.path.isdir(os.path.join(hot_root, name)):
            continue
        try:
            age = _day_age(name)
        except ValueError:
            continue
        if age >= keep_days:
            ages[name] = age
    return sorted(ages, key=ages.get, reverse=True)  # сначала самые старые


def _remove_with_wal_shm(path):
    """Удаляет `path` и его sqlite-спутники `-wal`/`-shm`, если они есть."""
    os.remove(path)
    for suffix in ("-wal", "-shm"):
        sidecar = path + suffix
        if os.path.isfile(sidecar):
            os.remove(sidecar)


def prune_hot(hot_root, cap_bytes, keep_days=7):
    """Удаляет сначала старые `metrics.db`, потом `procs.db` у дней старше
    `keep_days` суток (с их `-wal`/`-shm`, если есть), пока `hot_size_bytes`
    не станет `<= cap_bytes` или удалять больше нечего; `containers/`,
    `journal.log*` и сегодняшний день — никогда, независимо от `keep_days`
    (в т.ч. `keep_days <= 0`, круг 1 ревью). Возвращает список удалённых
    основных путей (без `-wal`/`-shm`) в порядке удаления.
    """
    deleted = []
    if hot_size_bytes(hot_root) <= cap_bytes:
        return deleted
    eligible = _eligible_days(hot_root, keep_days)
    for filename in ("metrics.db", "procs.db"):
        for day in eligible:
            if hot_size_bytes(hot_root) <= cap_bytes:
                return deleted
            path = os.path.join(hot_root, day, filename)
            if os.path.isfile(path):
                _remove_with_wal_shm(path)
                deleted.append(path)
    return deleted
