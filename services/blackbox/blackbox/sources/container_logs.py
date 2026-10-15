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
    """Дочитывание файлов `json-file` всех контейнеров с запомненной позиции."""

    def __init__(self, state):
        self._state = state

    def read_new(self, name, path, max_bytes=4 << 20):
        """Новые строки `"log"` с прошлой позиции (не более `max_bytes` за вызов)."""
        try:
            stat = os.stat(path)
        except OSError:
            return []
        cursor = self._state.get(name)
        offset = _resolve_offset(cursor, stat)
        with open(path, "rb") as fh:
            fh.seek(offset)
            chunk = fh.read(max_bytes)
        lines, consumed = _split_complete_lines(chunk)
        self._state[name] = {"inode": stat.st_ino, "offset": offset + consumed}
        return [value for value in (_extract_log_field(line) for line in lines)
                if value is not None]


# ── split_health / tail_lines ───────────────────────────────────────────────

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
    while pos > 0 and newline_count <= n:
        step = min(block_size, pos)
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
