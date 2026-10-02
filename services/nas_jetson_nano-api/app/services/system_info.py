"""
Системные метрики Jetson: /proc, /sys/class/thermal и Docker Engine API.

Вынесено из app/routers/system.py (CQ-02, docs/audit/2026-10-02_code_audit/REPORT.ru.md
§4, §6): раньше app/routers/talk_bot.py звал эти функции напрямую как приватные
(`system_mod._read_meminfo`, `system_mod._docker_ps_json` и т.д.) — переименование
внутри роутера молча ломало бы бота, а тесты роутера этого не видели. Логика не
менялась, только место и имена верхнего уровня (без ведущего `_`, раз они теперь
публичный API сервисного слоя).
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx

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
# Docker helpers (via Docker Engine socket, fallback to CLI; no docker-py dep)
# ---------------------------------------------------------------------------

async def docker_ps_json() -> list[dict]:
    socket_path = "/var/run/docker.sock"
    if Path(socket_path).exists():
        try:
            transport = httpx.AsyncHTTPTransport(uds=socket_path)
            async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
                response = await client.get("http://docker/containers/json", params={"all": "1"})
            response.raise_for_status()
            result = []
            for item in response.json():
                names = item.get("Names") or []
                name = names[0].lstrip("/") if names else item.get("Id", "")[:12]
                result.append({
                    "name": name,
                    "status": item.get("Status", ""),
                    "image": item.get("Image", ""),
                    "state": item.get("State", ""),
                })
            return result
        except Exception as exc:
            log.warning("docker socket query failed: %s", exc)

    fmt = '{"name":"{{.Names}}","status":"{{.Status}}","image":"{{.Image}}","state":"{{.State}}"}'
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--format", fmt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        result = []
        for line in stdout.decode().splitlines():
            line = line.strip()
            if line:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return result
    except Exception as exc:
        log.warning("docker ps failed: %s", exc)
        return []
