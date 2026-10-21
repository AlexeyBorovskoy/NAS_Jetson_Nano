"""Дочитывание журналов контейнеров `json-file` (OBS-1, задача 4,
спецификация §4.1, цикл logs).

Формат `json-file`: одна физическая строка файла = один JSON-объект
`{"log": "...", "stream": "...", "time": "..."}`; возвращаемые значения —
содержимое поля `"log"` как есть (вместе с переводом строки внутри него).

Состояние `{имя: {"inode", "offset"}}` хранит вызывающий (`Catalog`, курсор
`set_cursor("logs", json)`); `LogTailer` получает тот же словарь и обновляет
его на месте — он обязан переживать JSON-сериализацию (только `int`/`str`).

Ротация (новый inode) и усечение (тот же inode, файл короче смещения) —
чтение нового содержимого с начала; неполная последняя строка (без
завершающего `\\n`) не потребляется до следующего вызова.

Python 3.6 (хост Jetson): только стандартная библиотека.
"""
import json
import os
import re

TAIL_READ_MAX_BYTES = 1 << 20


def _resolve_offset(cursor, stat):
    """Смещение чтения: 0 при смене inode или усечении, иначе прежнее смещение."""
    if cursor is None:
        return 0
    if cursor.get("inode") != stat.st_ino:
        return 0
    if stat.st_size < cursor.get("offset", 0):
        return 0
    return cursor["offset"]


def _split_complete_lines(chunk):
    """(список_физических_строк_без_\\n, сколько_байт_потрачено) — хвост без `\\n` не потребляется."""
    parts = chunk.split(b"\n")
    if chunk.endswith(b"\n"):
        parts.pop()  # пустая строка после последнего "\n"
    else:
        parts.pop()  # неполная последняя строка — вернуть в файл
    consumed = sum(len(part) + 1 for part in parts)
    return parts, consumed


def _extract_log_field(line):
    """Физическая строка (JSON-объект, без `\\n`) -> значение поля `"log"`, либо `None`."""
    try:
        record = json.loads(line)
    except ValueError:
        return None
    return record.get("log")


class LogTailer(object):
    """Read JSON log files with a bounded initial tail."""

    INITIAL_GAP = "[blackbox: initial log backlog omitted: {bytes} bytes]\n"
    OVERSIZED_GAP = "[blackbox: oversized log record omitted]\n"

    def __init__(self, state, initial_tail_bytes=None):
        self._state = state
        self._initial_tail_bytes = initial_tail_bytes

    def read_new(self, name, path, max_bytes=4 << 20):
        """Read complete JSON records using at most `max_bytes`."""
        if max_bytes <= 0:
            return []
        try:
            stat = os.stat(path)
        except OSError:
            return []
        previous = self._state.get(name)
        offset, reset = self._cursor_offset(previous, stat)
        bounded = self._initial_tail_bytes is not None
        cursor = self._make_cursor(previous, stat, offset, bounded)
        if reset:
            if "discarding" in cursor:
                cursor["discarding"] = False
                cursor["discard_reason"] = ""
                cursor["pending_bytes"] = 0
            self._start_at_tail(cursor, stat.st_size)
        with open(path, "rb") as fh:
            fh.seek(cursor["offset"])
            chunk = fh.read(max_bytes)
        values = self._consume(cursor, chunk, max_bytes)
        if bounded or "size" in cursor:
            cursor["size"] = stat.st_size
        self._state[name] = cursor
        return values

    @staticmethod
    def _cursor_offset(cursor, stat):
        if cursor is None or cursor.get("inode") != stat.st_ino:
            return 0, True
        offset = cursor.get("offset", 0)
        prior_size = cursor.get("size", offset)
        if (not isinstance(offset, int) or offset < 0 or
                not isinstance(prior_size, int) or stat.st_size < max(offset, prior_size)):
            return 0, True
        return offset, False

    @staticmethod
    def _make_cursor(previous, stat, offset, bounded):
        cursor = dict(previous) if isinstance(previous, dict) else {}
        cursor.update({"inode": stat.st_ino, "offset": offset})
        if bounded or any(key in cursor for key in (
                "discarded", "oversized", "discarding", "discard_reason")):
            LogTailer._ensure_budget_fields(cursor)
            cursor.setdefault("size", stat.st_size)
        return cursor

    @staticmethod
    def _ensure_budget_fields(cursor):
        cursor.setdefault("discarded", 0)
        cursor.setdefault("oversized", 0)
        cursor.setdefault("discarding", False)
        cursor.setdefault("discard_reason", "")
        cursor.setdefault("pending_bytes", 0)
        cursor.setdefault("size", 0)

    def _start_at_tail(self, cursor, size):
        budget = self._initial_tail_bytes
        if not isinstance(budget, int) or budget <= 0 or size <= budget:
            return
        self._ensure_budget_fields(cursor)
        skipped = size - budget
        cursor["offset"] = skipped
        cursor["discarded"] += skipped
        cursor["pending_bytes"] = skipped
        cursor["discarding"] = True
        cursor["discard_reason"] = "initial"

    def _consume(self, cursor, chunk, max_bytes):
        if cursor.get("discarding", False):
            return self._consume_discard(cursor, chunk, max_bytes)
        if not chunk:
            return []
        if b"\n" not in chunk and len(chunk) == max_bytes:
            self._ensure_budget_fields(cursor)
            self._advance(cursor, len(chunk))
            cursor["discarded"] += len(chunk)
            cursor["oversized"] += 1
            cursor["discarding"] = True
            cursor["discard_reason"] = "oversized"
            cursor["pending_bytes"] = 0
            return [self.OVERSIZED_GAP]
        lines, consumed = _split_complete_lines(chunk)
        self._advance(cursor, consumed)
        return [value for value in (_extract_log_field(line) for line in lines)
                if value is not None]

    def _consume_discard(self, cursor, chunk, max_bytes):
        if not chunk:
            return []
        boundary = chunk.find(b"\n")
        if boundary < 0:
            self._advance(cursor, len(chunk))
            cursor["discarded"] += len(chunk)
            if cursor["discard_reason"] == "initial":
                cursor["pending_bytes"] += len(chunk)
            return []
        discarded = boundary + 1
        self._advance(cursor, discarded)
        cursor["discarded"] += discarded
        reason = cursor["discard_reason"]
        cursor["discarding"] = False
        cursor["discard_reason"] = ""
        values = []
        if reason == "initial":
            values.append(self.INITIAL_GAP.format(
                bytes=cursor["pending_bytes"] + discarded))
            cursor["pending_bytes"] = 0
        remainder = chunk[discarded:]
        if remainder:
            values.extend(self._consume(cursor, remainder, max_bytes))
        return values

    @staticmethod
    def _advance(cursor, count):
        cursor["offset"] += count


#: Пути проверок здоровья (раздел 4.1, цикл logs) — считаются, а не хранятся строками.
_HEALTH_PATHS = ("/health", "/healthcheck", "/status.php")

_REQUEST_RE = re.compile(r'"GET\s+(\S+)\s+HTTP/[\d.]+"\s+(\d{3})')


def split_health(lines):
    """(kept, health_count) — строки доступа GET на `_HEALTH_PATHS` с кодом 200 уходят в счётчик."""
    kept = []
    health_count = 0
    for line in lines:
        match = _REQUEST_RE.search(line)
        if match and match.group(1) in _HEALTH_PATHS and match.group(2) == "200":
            health_count += 1
            continue
        kept.append(line)
    return kept, health_count


def _read_tail_bytes(fh, n, block_size):
    """Байты с конца файла, достаточные для `n` физических строк (или весь файл).

    Читает блоками по `block_size` от конца к началу, а не файл целиком —
    правка круга 1 ревью (КРИТИЧНОЕ): `json-file` на аварии контейнера может
    весить сотни МБ при пределе сборщика 64 МБ, и старое `fh.readlines()`
    было OOM-ловушкой ровно в момент, когда нужны последние строки.
    Память — O(размера накопленного хвоста), не O(размера файла).

    Условие остановки — `newline_count > n` (на одну границу БОЛЬШЕ, чем
    строк нужно), не `>= n`: если прочитанный хвост начинается не ровно на
    границе строки, его первый элемент после `split(b"\\n")` — обрубок
    предыдущей строки, а не нужная строка. `_extract_log_field` такой обрубок
    не распарсит и тихо выбросит как `None`, и результат окажется короче `n`
    без единой ошибки (ровно так и проявился этот дефект на обзоре). Лишняя
    граница гарантирует, что обрубок окажется за пределами взятых `n`
    последних элементов, а `pos == 0` (дошли до начала файла) — тот же самый
    случай, но без обрубка вовсе: там граница не нужна, начало файла само
    по себе чистая граница.
    """
    fh.seek(0, os.SEEK_END)
    pos = fh.tell()
    data = b""
    newline_count = 0
    while pos > 0 and newline_count <= n and len(data) < TAIL_READ_MAX_BYTES:
        step = min(block_size, pos, TAIL_READ_MAX_BYTES - len(data))
        pos -= step
        fh.seek(pos)
        data = fh.read(step) + data
        newline_count = data.count(b"\n")
    return data


def tail_lines(path, n=200, block_size=64 << 10):
    """Последние `n` строк `"log"` файла `json-file` (для событий die/oom/unhealthy).

    Файл, исчезнувший между вызовами (ротация/удаление под ногами) -> `[]`,
    как и `LogTailer.read_new` — не бросает исключение (правка круга 1,
    ВАЖНОЕ 2).
    """
    if n <= 0:
        return []
    try:
        with open(path, "rb") as fh:
            data = _read_tail_bytes(fh, n, block_size)
    except OSError:
        return []
    lines = data.split(b"\n")
    if data.endswith(b"\n"):
        lines.pop()  # пустая строка после последнего "\n"
    tail = lines[-n:]
    return [value for value in (_extract_log_field(line) for line in tail)
            if value is not None]
