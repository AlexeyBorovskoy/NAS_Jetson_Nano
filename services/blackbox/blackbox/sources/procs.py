"""Источник «процессы» (OBS-1, задача 6).

Читает подставной или живой /proc только файлами: субпроцессы не запускаются,
`environ` не читается. Все чтения ограничены по объёму; исчезнувший, закрытый
правами или испорченный процесс пропускается, а не роняет обход.

Python 3.6: только стандартная библиотека, без dataclasses и `:=`.
"""
import os
import re

#: Ид контейнера Docker — 64 шестнадцатеричных знака после `/docker/` или в
#: имени юнита cgroupfs `docker-<id>.scope`.
_DOCKER_ID_RE = re.compile(r"(?:/docker/|docker-)([0-9a-f]{64})(?:\.scope)?(?![0-9a-f])")

_COMM_MAX = 256
_CMD_MAX = 4096
_STAT_MAX = 4096
_WCHAN_MAX = 128
_CGROUP_MAX = 16384

_MIB = 1024.0 * 1024.0


def _page_size():
    """Размер страницы для поля rss; без `os.sysconf` (Windows) — 4096."""
    try:
        return int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, ValueError, OSError):
        return 4096


_PAGE_SIZE = _page_size()


def _read(path, limit):
    """Не больше `limit` байт файла, декодирование с заменой ошибок."""
    with open(path, "rb") as fh:
        return fh.read(limit).decode("utf-8", "replace")


def _read_opt(path, limit):
    """Как `_read`, но отсутствие файла или прав — пустая строка."""
    try:
        return _read(path, limit)
    except OSError:
        return ""


def _num(value):
    """Число или None, если значение отсутствует или не число."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def container_of(proc_root, id_map):
    """Фабрика резолвера owner: cgroup процесса -> имя контейнера или «host».

    Понимает v1/v2-записи `/docker/<id>` и cgroupfs-форму
    `docker-<id>.scope`. Нераспознанный или несопоставленный ид — «host».
    """
    def resolve(pid):
        text = _read_opt(os.path.join(proc_root, str(pid), "cgroup"), _CGROUP_MAX)
        match = _DOCKER_ID_RE.search(text)
        if match is None:
            return "host"
        return id_map.get(match.group(1), "host")

    return resolve


def _parse_stat(text):
    """(comm, state, ticks, start, rss_pages) из /proc/<pid>/stat.

    comm берётся между первой `(` и последней `)`: имя процесса может содержать
    и пробелы, и скобки, а поля после него — только числа и буква состояния.
    """
    lparen = text.find("(")
    rparen = text.rfind(")")
    if lparen < 0 or rparen < lparen:
        raise ValueError("stat: нет comm")
    fields = text[rparen + 1:].split()
    if len(fields) < 22:
        raise ValueError("stat: мало полей")
    ticks = int(fields[11]) + int(fields[12])     # поля 14 utime + 15 stime
    return (text[lparen + 1:rparen], fields[0], ticks,
            int(fields[19]), int(fields[21]))    # поля 22 start, 24 rss


def _rss_mb(pages):
    """Страницы -> МиБ."""
    return round(pages * _PAGE_SIZE / _MIB, 1)


def _read_one(proc_root, name, resolver):
    """Сырая запись процесса или None, если он исчез/недоступен/испорчен."""
    base = os.path.join(proc_root, name)
    try:
        parsed = _parse_stat(_read(os.path.join(base, "stat"), _STAT_MAX))
    except (OSError, ValueError):
        return None
    stat_comm, state, ticks, start, pages = parsed
    comm = _read_opt(os.path.join(base, "comm"), _COMM_MAX).strip() or stat_comm
    cmd = _read_opt(os.path.join(base, "cmdline"), _CMD_MAX)
    try:
        owner = resolver(int(name))
    except Exception:            # сбой резолвера не должен терять процесс
        owner = "host"
    return {"pid": int(name), "comm": comm,
            "cmd": cmd.replace(chr(0), " ").strip()[: _CMD_MAX], "state": state,
            "wchan": _read_opt(os.path.join(base, "wchan"), _WCHAN_MAX).strip(),
            "ticks": ticks, "start": start, "rss_mb": _rss_mb(pages),
            "owner": owner}


def read_procs(proc_root, container_of):
    """Записи всех читаемых процессов дерева /proc (ключи — контракт плана)."""
    records = []
    for name in sorted(os.listdir(proc_root)):
        if not name.isdigit():
            continue
        record = _read_one(proc_root, name, container_of)
        if record is not None:
            records.append(record)
    return records


def _cpu_pct(prev, cur, rate):
    """Загрузка CPU в процентах; `rate` — 100/(hz·dt) либо None при плохом интервале."""
    if rate is None:
        return 0.0
    ticks = _num(cur.get("ticks"))
    if ticks is None:
        return 0.0
    delta = ticks
    if prev is not None and prev.get("start") == cur.get("start"):
        before = _num(prev.get("ticks"))
        delta = ticks if before is None else ticks - before
    return max(delta, 0.0) * rate       # PID переиспользован или счётчик сброшен


def _select(rows, top_n):
    """Объединение топ-N по CPU, топ-N по RSS и всех D-state, без дублей."""
    limit = top_n if isinstance(top_n, int) and top_n > 0 else 0
    picked = {}
    for key in ("cpu_pct", "rss_mb"):
        ordered = sorted(rows, key=lambda r: (-(_num(r[key]) or 0.0), r["pid"]))
        for row in ordered[:limit]:
            picked[row["pid"]] = row
    for row in rows:
        if row.get("state") == "D":
            picked[row["pid"]] = row
    return list(picked.values())


def snapshot(prev_raw, cur_raw, dt_s, hz, ts, top_n=10):
    """Снимок процессов: топ-10 CPU/RSS плюс все D-state, порядок — по PID."""
    dt = _num(dt_s)
    hz_value = _num(hz)
    rate = None
    if dt is not None and hz_value is not None and dt > 0 and hz_value > 0:
        rate = 100.0 / (hz_value * dt)
    prev_by_pid = {rec.get("pid"): rec for rec in (prev_raw or [])}
    rows = []
    for rec in cur_raw:
        pid = rec.get("pid")
        if pid is None:
            continue
        rows.append({
            "ts": ts, "pid": pid, "comm": rec.get("comm", ""),
            "owner": rec.get("owner", "host"), "cmd": rec.get("cmd", ""),
            "state": rec.get("state", "?"), "wchan": rec.get("wchan", ""),
            "cpu_pct": _cpu_pct(prev_by_pid.get(pid), rec, rate),
            "rss_mb": _num(rec.get("rss_mb")) or 0.0,
        })
    return sorted(_select(rows, top_n), key=lambda r: r["pid"])


def _is_below(value, limit):
    number = _num(value)
    bound = _num(limit)
    return number is not None and bound is not None and number < bound


def _is_above(value, limit):
    number = _num(value)
    bound = _num(limit)
    return number is not None and bound is not None and number > bound


def _swap_growth_high(sample, prev_sample, limit):
    """Рост подкачки выше порога в МБ/мин; нет прошлого замера — не аномалия."""
    if not prev_sample:
        return False
    current = _num(sample.get("swap_mb"))
    before = _num(prev_sample.get("swap_mb"))
    now = _num(sample.get("ts"))
    then = _num(prev_sample.get("ts"))
    bound = _num(limit)
    if None in (current, before, now, then, bound) or now - then <= 0:
        return False
    return (current - before) / (now - then) * 60.0 > bound


def is_anomaly(sample, prev_sample, d_count, cfg):
    """Аномалия: D-state, мало памяти, высокая load1 или быстрый рост подкачки."""
    if (_num(d_count) or 0.0) > 0:
        return True
    if _is_below(sample.get("mem_avail_mb"), cfg.mem_low_mb):
        return True
    if _is_above(sample.get("load1"), cfg.load_high):
        return True
    return _swap_growth_high(sample, prev_sample, cfg.swap_growth_mb_min)
