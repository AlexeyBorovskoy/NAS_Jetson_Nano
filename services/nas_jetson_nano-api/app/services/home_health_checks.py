"""Bounded health probes; unavailable evidence remains unknown."""
from __future__ import annotations

import asyncio
import json


async def reap_process(proc, timeout: float) -> None:
    if proc is not None and proc.returncode is None:
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except (OSError, asyncio.TimeoutError):
            try:
                proc.kill()
            except OSError:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except (OSError, asyncio.TimeoutError):
                pass  # cleanup тоже ограничен; недоступность проверки остаётся unknown


def read_active_alerts(path: str) -> list[str] | None:
    """Phase E (scripts/monitoring/nas_jetson_nano-talk-alert.py) уже проверяет то,
    что из контейнера API не проверить вовсе — SMART HDD, swap, off-site бэкап,
    квоты GigaChat, расходы Cloud.ru. Читаем готовый снимок, а не пересчитываем.
    None = снимок недоступен или некорректен, [] = корректный снимок без алертов.
    Остальные прямые проверки от снимка не зависят."""
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    if any(not isinstance(v, dict) or not isinstance(v.get("active"), bool)
           or not isinstance(v.get("text", ""), str) for v in state.values()):
        return None
    return [v.get("text") or key for key, v in state.items()
            if v.get("active")]


async def storage_problems(storage_mod, warn_pct: int, max_age: int):
    problems, unknown = [], []
    ssd = await storage_mod.disk_info(storage_mod.STORAGE_ROOT)
    if ssd.get("error"):
        unknown.append("SSD /mnt/storage (ошибка чтения или таймаут)")
    elif not ssd.get("mounted"):
        problems.append("SSD /mnt/storage не смонтирован")
    else:
        if ssd.get("used_pct", 0) >= warn_pct:
            problems.append("SSD почти заполнен — %s%%" % ssd["used_pct"])
        backups = await storage_mod.backup_info()
        if not backups.get("available"):
            unknown.append("бэкапы (каталог недоступен)")
        for d in backups.get("dumps", []):
            age = d.get("age_hours")
            if age is None:
                problems.append("нет дампа %s" % d["db"])
            elif age > max_age:
                problems.append("бэкап %s устарел — %dч назад" % (d["db"], age))

    return problems, unknown


async def container_problems(system_info, names: str):
    problems, unknown = [], []
    try:
        expected = set(names.split())
        containers = await system_info.docker_ps_json()
        observed = {c.get("name"): c.get("state", "").lower() for c in containers}
        down = sorted(name for name in expected if name in observed and observed[name] != "running")
        missing = sorted(expected - observed.keys())
        if missing:
            unknown.append("ожидаемые контейнеры отсутствуют в списке Docker: %s" % ", ".join(missing))
        if down:
            problems.append("не работают контейнеры: %s" % ", ".join(down))
    except Exception as exc:
        unknown.append("контейнеры (%s)" % type(exc).__name__)

    return problems, unknown
