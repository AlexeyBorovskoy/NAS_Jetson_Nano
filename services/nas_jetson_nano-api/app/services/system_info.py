"""
Системные метрики Jetson: /proc, /sys/class/thermal и статус Docker — только
чтение, через HTTP-прокси (DP-2, 2026-10-09: ни UNIX-сокета, ни вызова CLI).

Вынесено из app/routers/system.py (CQ-02, docs/audit/2026-10-02_code_audit/REPORT.ru.md
§4, §6): раньше app/routers/talk_bot.py звал эти функции напрямую как приватные
(`system_mod._read_meminfo`, `system_mod._docker_ps_json` и т.д.) — переименование
внутри роутера молча ломало бы бота, а тесты роутера этого не видели. Логика не
менялась, только место и имена верхнего уровня (без ведущего `_`, раз они теперь
публичный API сервисного слоя).
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import HTTPException

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.services.system_info")


# ---------------------------------------------------------------------------
# Helpers — read from /proc and /sys (no external deps)
# ---------------------------------------------------------------------------

def read_meminfo() -> dict:
    data: dict = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                data[parts[0].rstrip(":")] = int(parts[1])
    except OSError:
        pass
    total_kb = data.get("MemTotal", 0)
    avail_kb = data.get("MemAvailable", 0)
    used_kb = total_kb - avail_kb
    return {
        "total_mb": total_kb // 1024,
        "used_mb": used_kb // 1024,
        "available_mb": avail_kb // 1024,
        "used_pct": round(used_kb / total_kb * 100, 1) if total_kb else 0,
    }


def read_loadavg() -> dict:
    try:
        parts = Path("/proc/loadavg").read_text().split()
        return {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}
    except OSError:
        return {}


def read_uptime_seconds() -> float:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except OSError:
        return 0.0


def read_thermal() -> list[dict]:
    zones = []
    WANTED = {"CPU-therm", "GPU-therm", "PLL-therm", "AO-therm", "PMIC-Die", "thermal-fan-est"}
    for zone_dir in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        try:
            name = (zone_dir / "type").read_text().strip()
            if name not in WANTED:
                continue
            temp_c = int((zone_dir / "temp").read_text().strip()) // 1000
            zones.append({"zone": name, "temp_c": temp_c})
        except OSError:
            continue
    return zones


# ---------------------------------------------------------------------------
# Docker status — только чтение через статусный HTTP-прокси (DP-2, 2026-10-09).
# У процесса API больше нет ни UNIX-сокета, ни вызова CLI.
# ---------------------------------------------------------------------------

def _normalize_container(item: dict) -> dict:
    if not isinstance(item, dict):
        raise ValueError("Invalid container record")
    names = item.get("Names", [])
    if not isinstance(names, list):
        raise ValueError("Invalid container names")
    name = names[0] if names else item.get("Id", "")[:12]
    if not isinstance(name, str) or not name:
        raise ValueError("Missing container identity")
    result = {"name": name.lstrip("/"), "status": item.get("Status", ""),
              "image": item.get("Image", ""), "state": item.get("State", "")}
    if not all(isinstance(value, str) for value in result.values()):
        raise ValueError("Invalid container fields")
    return result


async def docker_ps_json() -> list[dict]:
    """Read status through the proxy; unavailable evidence is 503, with no fallback."""
    url = f"{settings.docker_status_url.rstrip('/')}/containers/json"
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False,
                                     follow_redirects=False) as client:
            response = await client.get(url, params={"all": "1"})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Invalid Docker status payload")
        return [_normalize_container(item) for item in payload]
    except Exception as exc:
        log.warning("docker status unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Docker status unavailable") from exc
