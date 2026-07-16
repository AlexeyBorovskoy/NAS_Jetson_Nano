"""
/v1/metrics  — CPU, RAM, disk, Jetson thermal zones
/v1/containers — Docker container status list
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.system")
router = APIRouter(prefix="/v1", tags=["Система"])


# ---------------------------------------------------------------------------
# Helpers — read from /proc and /sys (no external deps)
# ---------------------------------------------------------------------------

def _read_meminfo() -> dict:
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


def _read_loadavg() -> dict:
    try:
        parts = Path("/proc/loadavg").read_text().split()
        return {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}
    except OSError:
        return {}


def _read_uptime_seconds() -> float:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except OSError:
        return 0.0


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


def _read_thermal() -> list[dict]:
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

async def _docker_ps_json() -> list[dict]:
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
        "ram": _read_meminfo(),
        "load": _read_loadavg(),
        "uptime_seconds": _read_uptime_seconds(),
        "disks": [_read_disk(p) for p in disk_paths],
        "thermal": _read_thermal(),
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
    all_containers = await _docker_ps_json()

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
