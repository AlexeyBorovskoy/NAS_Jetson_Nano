"""
/v1/storage — Storage layer status: SSD mount, disk usage, backup dumps.
Protected endpoint: requires valid JWT.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.routers.auth import require_auth

log = logging.getLogger("nas_jetson_nano_api.storage")
router = APIRouter(prefix="/v1", tags=["Хранилище"])

STORAGE_ROOT = Path("/mnt/storage")
BACKUP_DIR = STORAGE_ROOT / "backups" / "database-dumps"


def _disk_info(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "mounted": False}
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        # Check it's actually a separate mountpoint (not root)
        root_dev = os.stat("/").st_dev
        path_dev = os.stat(path).st_dev
        return {
            "path": str(path),
            "mounted": path_dev != root_dev,
            "total_gb": round(total / 1024 ** 3, 1),
            "used_gb": round(used / 1024 ** 3, 1),
            "free_gb": round(free / 1024 ** 3, 1),
            "used_pct": round(used / total * 100, 1) if total else 0,
        }
    except OSError as exc:
        return {"path": str(path), "mounted": False, "error": str(exc)}


def _backup_info() -> dict:
    if not BACKUP_DIR.exists():
        return {"available": False, "dumps": []}
    dumps = []
    for db in ("nextcloud", "immich"):
        files = sorted(BACKUP_DIR.glob(f"{db}_*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            f = files[0]
            st = f.stat()
            age_hours = int((Path("/proc/uptime").read_text().split()[0] and
                             __import__("time").time() - st.st_mtime) / 3600)
            dumps.append({
                "db": db,
                "file": f.name,
                "size_mb": round(st.st_size / 1024 ** 2, 1),
                "age_hours": age_hours,
                "count_total": len(files),
            })
        else:
            dumps.append({"db": db, "file": None, "size_mb": 0, "age_hours": None})
    return {"available": True, "path": str(BACKUP_DIR), "dumps": dumps}


@router.get(
    "/storage",
    summary="Состояние хранилища",
    description=(
        "Статус SSD (`/mnt/storage`): смонтирован ли, использование диска, "
        "наличие и возраст DB-дампов (Nextcloud + Immich). "
        "**Требует Bearer JWT** (получить через `POST /api/auth/login`)."
    ),
)
async def storage_status(username: Annotated[str, Depends(require_auth)]):
    ssd = _disk_info(STORAGE_ROOT)
    backups = _backup_info() if ssd.get("mounted") else {"available": False, "reason": "ssd not mounted"}

    healthy = ssd.get("mounted", False)
    log.info("storage queried by %s — mounted=%s", username, healthy)

    return JSONResponse(content={
        "storage_healthy": healthy,
        "ssd": ssd,
        "backups": backups,
    })
