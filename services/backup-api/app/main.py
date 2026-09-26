"""
Home Cloud — Backup API (Stage 2 placeholder).

Stage 1: сервис не разворачивается на боевом Jetson. Скелет нужен для:
  - стабилизации API-контракта с будущим Android-клиентом;
  - запуска в mock-режиме (BACKUP_API_ENABLED=0) для unit-тестов и demo;
  - проверки CI/линтеров до Stage 2.

Stage 2 включит работу с диском, базой и upload-ом — после отдельного RFC.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field


# ── Конфиг (env) ──────────────────────────────────────────────────────────────

API_PORT = int(os.getenv("BACKUP_API_PORT", "8095"))
API_TOKEN = os.getenv("BACKUP_API_TOKEN", "")
STORAGE_ROOT = Path(os.getenv("BACKUP_API_STORAGE_ROOT", "/mnt/storage/backups/devices"))
ENABLED = os.getenv("BACKUP_API_ENABLED", "0") == "1"

app = FastAPI(
    title="Home Cloud Backup API",
    version="0.1.0",
    description="Stage 2 placeholder. Не использовать в production без отдельного RFC.",
)


# ── Auth ──────────────────────────────────────────────────────────────────────

def require_bearer(authorization: Annotated[Optional[str], Header()] = None) -> str:
    """Bearer-токен. В mock-режиме допускается отсутствие токена."""
    if not ENABLED:
        return "mock"
    if not API_TOKEN or API_TOKEN.startswith("change_me"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "BACKUP_API_TOKEN is not configured",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(token, API_TOKEN):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return token


# ── Pydantic-модели API ───────────────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=120)
    platform: Literal["android", "ios", "other"] = "android"
    app_version: Optional[str] = Field(default=None, max_length=40)


class DeviceRegisterResponse(BaseModel):
    device_id: str
    registered_at: float


class BackupCreateRequest(BaseModel):
    device_id: str
    kind: Literal["photos", "contacts", "calendar", "sms", "documents", "full"] = "full"
    note: Optional[str] = Field(default=None, max_length=500)


class BackupCreateResponse(BaseModel):
    backup_id: str
    upload_url: str
    expires_at: float


class BackupListItem(BaseModel):
    backup_id: str
    device_id: str
    kind: str
    created_at: float
    size_bytes: int
    sha256: Optional[str]


class BackupListResponse(BaseModel):
    items: list[BackupListItem]


class RestorePlanRequest(BaseModel):
    device_id: str
    backup_id: str
    targets: list[Literal["photos", "contacts", "calendar", "sms", "documents"]]


class RestorePlanResponse(BaseModel):
    plan_id: str
    steps: list[str]


# ── Эндпоинты ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "real" if ENABLED else "mock",
        "storage_root": str(STORAGE_ROOT),
        "version": app.version,
    }


@app.post(
    "/api/v1/devices/register",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device(payload: DeviceRegisterRequest, _: str = Depends(require_bearer)):
    device_id = f"dev_{uuid.uuid4().hex[:16]}"
    if ENABLED:
        (STORAGE_ROOT / device_id).mkdir(parents=True, exist_ok=True)
    return DeviceRegisterResponse(device_id=device_id, registered_at=time.time())


@app.post(
    "/api/v1/backups/create",
    response_model=BackupCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_backup(payload: BackupCreateRequest, _: str = Depends(require_bearer)):
    backup_id = f"bk_{uuid.uuid4().hex[:24]}"
    return BackupCreateResponse(
        backup_id=backup_id,
        upload_url=f"/api/v1/backups/upload?backup_id={backup_id}",
        expires_at=time.time() + 3600,
    )


# BK-1 (аудит 2026-09-26): и backup_id, и имя файла приходят от клиента и шли в путь как
# есть — «bk_/../../x» и «../../x» писали за пределы STORAGE_ROOT.
_BACKUP_ID_RE = re.compile(r"^bk_[A-Za-z0-9_-]{1,64}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")


def _safe_target(backup_id: str, filename: Optional[str]) -> Path:
    if not _BACKUP_ID_RE.match(backup_id or ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid backup_id")
    name = (filename or "payload.bin").replace("\\", "/").rsplit("/", 1)[-1]
    if not _FILENAME_RE.match(name) or name in (".", ".."):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename")
    root = STORAGE_ROOT.resolve()
    out = (root / backup_id / name).resolve()
    try:
        out.relative_to(root / backup_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename") from None
    return out


@app.post("/api/v1/backups/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_backup(
    backup_id: str,
    file: UploadFile,
    _: str = Depends(require_bearer),
) -> dict:
    out_path = _safe_target(backup_id, file.filename)
    if not ENABLED:
        return {"backup_id": backup_id, "stored": False, "mode": "mock"}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(".%s.part" % out_path.name)
    sha = hashlib.sha256()
    size = 0
    try:
        with tmp_path.open("wb") as fh:
            while chunk := file.file.read(1024 * 1024):
                fh.write(chunk)
                sha.update(chunk)
                size += len(chunk)
        os.replace(tmp_path, out_path)  # оборванная загрузка не оставляет «готовый» файл
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return {
        "backup_id": backup_id,
        "stored": True,
        "path": str(out_path),
        "size_bytes": size,
        "sha256": sha.hexdigest(),
    }


@app.get("/api/v1/backups/list", response_model=BackupListResponse)
def list_backups(device_id: Optional[str] = None, _: str = Depends(require_bearer)):
    if not ENABLED:
        return BackupListResponse(items=[])
    items: list[BackupListItem] = []
    if not STORAGE_ROOT.exists():
        return BackupListResponse(items=items)
    for backup_dir in STORAGE_ROOT.glob("bk_*"):
        if not backup_dir.is_dir():
            continue
        for fp in backup_dir.iterdir():
            if not fp.is_file():
                continue
            items.append(
                BackupListItem(
                    backup_id=backup_dir.name,
                    device_id=device_id or "unknown",
                    kind="unknown",
                    created_at=fp.stat().st_mtime,
                    size_bytes=fp.stat().st_size,
                    sha256=None,
                )
            )
    return BackupListResponse(items=items)


@app.post(
    "/api/v1/restore/plan",
    response_model=RestorePlanResponse,
)
def plan_restore(payload: RestorePlanRequest, _: str = Depends(require_bearer)):
    plan_id = f"rp_{uuid.uuid4().hex[:16]}"
    steps = [
        f"verify backup {payload.backup_id} for device {payload.device_id}",
        *[f"restore {t}" for t in payload.targets],
        "report",
    ]
    return RestorePlanResponse(plan_id=plan_id, steps=steps)
