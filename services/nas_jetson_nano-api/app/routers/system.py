"""
/v1/metrics  — CPU, RAM, disk, Jetson thermal zones
/v1/containers — Docker container status list
"""

import asyncio
import logging
import os
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import blocking
from app.config import settings
from app.services import system_info

log = logging.getLogger("nas_jetson_nano_api.system")
router = APIRouter(prefix="/v1", tags=["Система"])


# ---------------------------------------------------------------------------
# Helpers — read from /proc and /sys (no external deps)
#
# read_meminfo/read_loadavg/read_uptime_seconds/read_thermal/docker_ps_json
# перенесены в app/services/system_info.py (CQ-02, аудит 2026-10-02): их звал как
# приватные чужой роутер (talk_bot.py), и переименование здесь молча ломало бы бота.
# ---------------------------------------------------------------------------

def _read_disk(path: str) -> dict:
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return {
            "path": path,
            "total_gb": round(total / 1024**3, 1),
            "used_gb": round(used / 1024**3, 1),
            "free_gb": round(free / 1024**3, 1),
            "used_pct": round(used / total * 100, 1) if total else 0,
        }
    except OSError:
        return {"path": path, "error": "unavailable"}


async def _read_disk_async(path: str) -> dict:
    """API-1: statvfs из потока с таймаутом — зависший HDD не останавливает цикл событий."""
    try:
        return await blocking.run_io("read_disk:%s" % path, _read_disk, path)
    except asyncio.TimeoutError:
        return {"path": path, "error": "timeout"}


async def _http_check(label: str, url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, follow_redirects=False)
        ok = r.status_code in (200, 302)
        return {"service": label, "url": url, "http_status": r.status_code, "ok": ok}
    except Exception as exc:
        return {"service": label, "url": url, "http_status": None, "ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/metrics",
    summary="Системные метрики Jetson",
    description=(
        "CPU load average, RAM (total/used/free), диск `/` и `/mnt/storage`, "
        "температурные зоны Jetson Nano (`/sys/class/thermal`). "
        "HTTP-статус локальных сервисов (Nextcloud/Immich/LLM GW)."
    ),
)
async def metrics():
    disk_paths = ["/"]
    if Path("/mnt/storage").exists():
        disk_paths.append("/mnt/storage")

    # HTTP checks for local services (run concurrently)
    svc_pairs = []
    for pair in settings.local_services.split():
        if "=" in pair:
            label, url = pair.split("=", 1)
            svc_pairs.append((label, url))

    http_results = await asyncio.gather(*[_http_check(l, u) for l, u in svc_pairs])

    payload = {
        "ram": system_info.read_meminfo(),
        "load": system_info.read_loadavg(),
        "uptime_seconds": system_info.read_uptime_seconds(),
        "disks": [await _read_disk_async(p) for p in disk_paths],
        "thermal": system_info.read_thermal(),
        "services_http": list(http_results),
    }

    all_ok = all(s["ok"] for s in http_results)
    log.info(
        "metrics polled",
        extra={"fields": {
            "ram_used_pct": payload["ram"].get("used_pct"),
            "services_ok": all_ok,
        }},
    )
    return JSONResponse(content=payload)


@router.get(
    "/containers",
    summary="Статус Docker-контейнеров",
    description=(
        "Список всех контейнеров (`docker ps -a`). "
        "Ожидаемые контейнеры (из `EXPECTED_CONTAINERS`) выделены флагом `expected: true`. "
        "Контейнеры не в состоянии `running` отмечены `healthy: false`."
    ),
)
async def containers():
    expected = set(settings.expected_containers.split())
    all_containers = await system_info.docker_ps_json()

    result = []
    unhealthy = []
    for c in all_containers:
        name = c.get("name", "")
        running = c.get("state", "").lower() == "running"
        exp = name in expected
        entry = {
            "name": name,
            "state": c.get("state", ""),
            "status": c.get("status", ""),
            "image": c.get("image", ""),
            "expected": exp,
            "healthy": running,
        }
        result.append(entry)
        if exp and not running:
            unhealthy.append(name)

    if unhealthy:
        log.warning(
            "unhealthy expected containers: %s", ", ".join(unhealthy),
            extra={"fields": {"unhealthy": unhealthy}},
        )

    return JSONResponse(content={"containers": result, "unhealthy_expected": unhealthy})
