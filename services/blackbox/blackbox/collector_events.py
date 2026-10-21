"""События сборщика «чёрного ящика» (OBS-1, задача 7): маскирование,
хвосты журналов и очередь событий Docker.

Всё, что попадает на диск (событие, хвост, командная строка процесса),
проходит `redact_line` **до** записи. Дополнительно скрывается остаток
командной строки после флага вида `--password`/`--token`/`--api-key` и
учётные данные из URL `scheme://user:password@host`. Вложенные строки
события обходятся до `REDACT_DEPTH`; глубже поддерево заменяется целиком
на `HIDDEN` (иначе секрет с глубины 6+ уходил бы в базу как есть).

Поток-производитель Docker — единственный поток сборщика: он кладёт сырые
события в ограниченную очередь `queue.Queue(1000)` неблокирующей записью,
считает отброшенные и переподключается через `shutdown.wait(5)`. Ни SQLite,
ни файлов в нём нет.

Python 3.6 (хост Jetson): только стандартная библиотека, без f-строк с `=`.
"""
import json
import os
import queue
import re
import threading
import time
from collections import deque

from blackbox.redact import HIDDEN, redact_line

#: Очередь событий Docker: предел, чтобы память не росла при зависшем SSD.
EVENT_QUEUE_MAX = 1000
#: Сколько событий забирать из очереди за один тик (цикл не должен стоять).
DRAIN_MAX = 500
#: Предел строк хвоста журнала контейнера (спецификация §4.1) и чтения.
TAIL_LINES_MAX = 200
LOG_READ_MAX_BYTES = 4 << 20
#: Пауза переподключения потока событий Docker, секунды.
RECONNECT_S = 5
#: Глубина рекурсии маскирования вложенных строк события.
REDACT_DEPTH = 5
MAX_EVENT_BYTES = 64 << 10
TAIL_BYTES_MAX = 16 << 10
EVENT_BUFFER_BYTES_MAX = 1 << 20

#: Флаги, после которых остаток командной строки скрывается целиком.
_SENSITIVE_FLAG_RE = re.compile(
    r"(?i)((?:^|\s)--?(?:password|passwd|pass|token|secret|api[-_]?key)"
    r"(?:=|\s))\S.*$")
#: Учётные данные в URL: `scheme://user:password@host`.
_URL_CRED_RE = re.compile(r"(?i)([a-z][a-z0-9+.\-]*://)[^/\s@]+@")


def _safe(call, default=None):
    """Вызов источника/преобразования: исключение — значение по умолчанию."""
    try:
        return call()
    except Exception:
        return default


# ── маскирование ─────────────────────────────────────────────────────────────

def scrub_text(text):
    """Прячет учётные данные URL и остаток строки после чувствительного флага."""
    return "".join(_scrub_line(line) for line in text.splitlines(True))


def _scrub_line(text):
    out = _URL_CRED_RE.sub(lambda m: m.group(1) + HIDDEN + "@", text)
    return _SENSITIVE_FLAG_RE.sub(lambda m: m.group(1) + HIDDEN, out)


def redact_text(owner, text, cfg):
    """redact_line + scrub + UTF-8 без суррогатов (битый `\\ud800` не роняет запись)."""
    lines = text.splitlines(True) or ([text] if text else [])
    out = "".join(scrub_text(redact_line(owner, line, cfg)) for line in lines)
    return out.encode("utf-8", "replace").decode("utf-8")


def redact_value(value, owner, cfg, depth):
    """Рекурсивно маскирует строки; глубже REDACT_DEPTH — поддерево целиком HIDDEN."""
    if depth > REDACT_DEPTH:
        return HIDDEN
    if isinstance(value, str):
        return redact_text(owner, value, cfg)
    if isinstance(value, dict):
        return dict((redact_value(key, owner, cfg, depth + 1),
                     redact_value(item, owner, cfg, depth + 1))
                    for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [redact_value(item, owner, cfg, depth + 1) for item in value]
    return value


def redact_event(event, cfg):
    """Копия события со всеми строковыми полями, прошедшими `redact_line`."""
    owner = event.get("subject") or ""
    return dict((key, redact_value(value, owner, cfg, 0))
                for key, value in event.items())


def redact_proc(row, cfg):
    """Копия строки процесса: маскируются `cmd`, `comm` и `wchan`."""
    owner = row.get("owner") or ""
    out = dict(row)
    for key in ("comm", "cmd", "wchan"):
        value = out.get(key)
        if isinstance(value, str):
            out[key] = redact_text(owner, value, cfg)
    return out


# ── хвосты журналов контейнеров ─────────────────────────────────────────────

def json_log_path(cfg, container_id):
    """Путь `json-file` контейнера Docker или `None`, если ид неизвестен."""
    if not container_id:
        return None
    return os.path.join(cfg.docker_root, "containers", container_id,
                        container_id + "-json.log")


def container_id(sources, cache, name):
    """Ид контейнера по имени; карта достраивается при первом обращении."""
    if name and name not in cache:
        for container in _safe(sources.containers, []) or []:
            cache[container.get("name")] = container.get("id")
    return cache.get(name)


def attach_tail(sources, cfg, event, cid):
    """Для die/oom/unhealthy — последние 200 строк журнала контейнера."""
    if event.get("kind") not in ("die", "oom", "unhealthy"):
        return
    path = json_log_path(cfg, cid)
    if path is None:
        return
    lines = _safe(lambda: sources.tail_lines(path, TAIL_LINES_MAX))
    if lines is None:
        return
    detail = dict(event.get("detail") or {})
    detail["tail"] = bounded_tail(lines, event.get("subject") or "", cfg)
    event["detail"] = detail


def bounded_tail(lines, owner, cfg, limit=TAIL_BYTES_MAX):
    """Redact whole lines first, then retain a bounded UTF-8 suffix."""
    selected = deque(lines, maxlen=TAIL_LINES_MAX)
    result = []
    used = 0
    for line in reversed(selected):
        safe = redact_text(owner, str(line), cfg)
        safe = safe if safe.endswith("\n") else safe + "\n"
        raw = safe.encode("utf-8")
        remaining = limit - used
        if remaining <= 12:
            break
        if len(raw) > remaining:
            suffix = raw[-(remaining - 12):].decode("utf-8", "replace")
            result.append("<truncated>" + suffix)
            break
        result.append(safe)
        used += len(raw)
    return list(reversed(result))


def serialized_size(value, limit=MAX_EVENT_BYTES, depth=0):
    """Measure bounded JSON UTF-8 size without constructing a serialized copy."""
    if depth > REDACT_DEPTH + 8:
        return limit + 1
    return _scalar_size(value, limit, depth)


def _scalar_size(value, limit, depth):
    if isinstance(value, str):
        return _json_string_size(value, limit)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return min(len(str(value)), limit + 1)
    if value is None or isinstance(value, bool):
        return len("null" if value is None else str(value).lower())
    return _container_size(value, limit, depth)


def _container_size(value, limit, depth):
    if isinstance(value, dict):
        return _dict_size(value, limit, depth)
    if isinstance(value, (list, tuple)):
        return _list_size(value, limit, depth)
    return limit + 1


def _dict_size(value, limit, depth):
    total = 2
    for index, (key, item) in enumerate(value.items()):
        if not isinstance(key, str):
            return limit + 1
        total += _entry_separator(index) + _json_string_size(key, limit - total) + 1
        total += serialized_size(item, limit - total, depth + 1)
        if total > limit:
            return limit + 1
    return total


def _list_size(value, limit, depth):
    total = 2
    for index, item in enumerate(value):
        total += _entry_separator(index) + serialized_size(item, limit - total, depth + 1)
        if total > limit:
            return limit + 1
    return total


def _entry_separator(index):
    return 1 if index else 0


def _json_string_size(text, limit):
    total = 2
    for char in text:
        code = ord(char)
        total += (2 if char in '\"\\\\' or code in (8, 9, 10, 12, 13)
                  else 6 if code < 32 else
                  1 if code < 128 else 2 if code < 2048 else
                  3 if code < 65536 else 4)
        if total > limit:
            return limit + 1
    return total


# ── контракт события ────────────────────────────────────────────────────────

def collector_event(ts, kind, severity, detail):
    """Событие источника `collector` (контракт `event`)."""
    return {"ts": int(ts), "source": "collector", "kind": kind,
            "subject": None, "severity": severity, "detail": dict(detail)}


def normalize_event(event, now):
    """Событие пробы/монтирования: `ts` и `source` по контракту, если их нет."""
    out = dict(event)
    out["ts"] = int(out.get("ts") or now)
    out.setdefault("source", "probe")
    return out


def docker_event(sources, raw, now):
    """Сырое событие Docker -> контракт `event` или `None` (не наше действие)."""
    event = _safe(lambda: sources.event_from_docker(raw))
    if not event:
        return None
    return normalize_event(event, now)


def parse_json_dict(raw):
    """JSON-объект из строки курсора/сводки или пустой dict (повреждённые данные)."""
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def event_from_fallback(row):
    """Строка `event` запасного каталога -> dict контракта."""
    _rowid, ts, source, kind, subject, severity, detail = row
    return {"ts": ts, "source": source, "kind": kind, "subject": subject,
            "severity": severity, "detail": parse_json_dict(detail)}


def event_signature(event):
    """Сигнатура события для дедупликации при переносе из запаса."""
    return (event.get("ts"), event.get("source"), event.get("kind"),
            event.get("subject"), event.get("severity"),
            json.dumps(event.get("detail") or {}, sort_keys=True,
                       ensure_ascii=False))


def event_time(raw, default):
    """Секунда события Docker для `since` переподключения."""
    value = raw.get("time") if isinstance(raw, dict) else None
    if isinstance(value, int) and value > default:
        return value
    return default


# ── поток событий Docker ────────────────────────────────────────────────────

def _event_producer(sources, out, shutdown, since, dropped, clock):
    """Демон-производитель: сырые события Docker -> ограниченная очередь.

    Ни SQLite, ни файлов здесь нет. Очередь переполнена — событие отбрасывается
    и учитывается в `dropped[0]`; разрыв потока — пауза `shutdown.wait(5)` и
    переподключение с последней известной секунды. Часы (`clock`) не нужны:
    пауза реальная, чтобы подставные часы не двигались потоком.
    """
    del clock
    while not shutdown.is_set():
        try:
            for raw in sources.events(int(since[0])):
                if shutdown.is_set():
                    return
                since[0] = event_time(raw, since[0])
                if not isinstance(raw, dict) or serialized_size(raw) > MAX_EVENT_BYTES:
                    dropped[0] += 1
                    continue
                try:
                    out.put_nowait(raw)
                except queue.Full:
                    dropped[0] += 1
        except Exception:          # обрыв сокета/JSON — переподключение
            pass
        shutdown.wait(RECONNECT_S)


class EventPump(object):
    """Очередь событий Docker: производитель-демон и неблокирующая выдача."""

    def __init__(self, sources, clock=time.time, maxsize=EVENT_QUEUE_MAX):
        self.sources = sources
        self.clock = clock
        self.queue = queue.Queue(maxsize=maxsize)
        self.dropped = [0]
        self.shutdown = threading.Event()
        self.thread = None

    def start(self, since=None):
        """Запускает поток-производитель (демон) с секунды `since`."""
        since = self.clock() if since is None else since
        self.thread = threading.Thread(
            target=_event_producer,
            args=(self.sources, self.queue, self.shutdown, [int(since)],
                  self.dropped, self.clock))
        self.thread.daemon = True
        self.thread.start()

    def drain(self, limit=DRAIN_MAX):
        """Забирает из очереди не больше `limit` сырых событий за тик."""
        items = []
        for _ in range(limit):
            try:
                items.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return items

    def take_dropped(self):
        """Отдаёт и обнуляет счётчик отброшенных событий."""
        count = self.dropped[0]
        self.dropped[0] = 0
        return count

    def stop(self, timeout=0.2):
        """Останавливает поток и ждёт его ограниченное время."""
        self.shutdown.set()
        if self.thread is not None:
            self.thread.join(timeout)
