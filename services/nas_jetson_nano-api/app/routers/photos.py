"""
/v1/photos — Immich photo library statistics.

Endpoints:
  GET /v1/photos/stats  — server-wide totals: assets, albums, storage
  GET /v1/photos/users  — per-user asset counts

Requires IMMICH_API_KEY env var (generate in Immich → Account Settings → API Keys).
All endpoints require JWT.
"""
from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.routers.auth import require_auth

log = logging.getLogger("nas_jetson_nano_api.photos")
router = APIRouter(prefix="/v1/photos", tags=["Фото — Immich"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _immich_headers() -> dict:
    if not settings.immich_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "IMMICH_API_KEY not configured. "
                "Generate it in Immich → Account Settings → API Keys, "
                "then set IMMICH_API_KEY in .env."
            ),
        )
    return {"x-api-key": settings.immich_api_key, "Accept": "application/json"}


async def _immich_get(path: str) -> dict | list:
    headers = _immich_headers()
    url = f"{settings.immich_internal_url}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Immich API key invalid or expired")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Immich API error: HTTP {r.status_code}")
    return r.json()


# ── Pydantic models ────────────────────────────────────────────────────────────

class PhotoStats(BaseModel):
    photos: int = Field(description="Total number of photos")
    videos: int = Field(description="Total number of videos")
    total_assets: int = Field(description="photos + videos")
    storage_used_bytes: int = Field(description="Total storage used by all assets")
    storage_used_gb: float = Field(description="Total storage used, in GB")


class AlbumStats(BaseModel):
    total_albums: int


class ServerStats(BaseModel):
    assets: PhotoStats
    albums: AlbumStats
    immich_version: str


class UserPhotoStats(BaseModel):
    user_id: str
    name: str
    email: str
    photos: int
    videos: int
    total_assets: int
    storage_used_bytes: int
    storage_used_gb: float


class UsersPhotoStats(BaseModel):
    total_users: int
    users: list[UserPhotoStats]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=ServerStats,
    summary="Статистика фотоархива Immich",
    description=(
        "Общая статистика фотоархива семьи: количество фото и видео, "
        "альбомы, занятое место на диске. "
        "Данные из Immich Admin API (`/api/server/statistics`). "
        "**Требует JWT** и переменной `IMMICH_API_KEY` в конфигурации."
    ),
)
async def photo_stats(_: Annotated[str, Depends(require_auth)]):
    # Server statistics
    stats = await _immich_get("api/server/statistics")
    photos_count = stats.get("photos", 0)
    videos_count = stats.get("videos", 0)
    storage_bytes = stats.get("usage", 0)

    # Server info for version
    try:
        info = await _immich_get("api/server/version")
        version = f"{info.get('major', 0)}.{info.get('minor', 0)}.{info.get('patch', 0)}"
    except HTTPException:
        version = "unknown"

    # Album count
    try:
        albums = await _immich_get("api/albums")
        total_albums = len(albums) if isinstance(albums, list) else 0
    except HTTPException:
        total_albums = 0

    storage_gb = round(storage_bytes / 1024 ** 3, 2)

    log.info(
        "photo stats: photos=%d videos=%d storage=%.2fGB",
        photos_count, videos_count, storage_gb,
        extra={"fields": {"photos": photos_count, "videos": videos_count, "storage_gb": storage_gb}},
    )
    return ServerStats(
        assets=PhotoStats(
            photos=photos_count,
            videos=videos_count,
            total_assets=photos_count + videos_count,
            storage_used_bytes=storage_bytes,
            storage_used_gb=storage_gb,
        ),
        albums=AlbumStats(total_albums=total_albums),
        immich_version=version,
    )


@router.get(
    "/users",
    response_model=UsersPhotoStats,
    summary="Статистика фото по пользователям",
    description=(
        "Количество фото и видео, а также занятое место для каждого пользователя Immich. "
        "Позволяет увидеть кто загружает больше всего. "
        "**Требует JWT** и переменной `IMMICH_API_KEY`."
    ),
)
async def photo_users_stats(_: Annotated[str, Depends(require_auth)]):
    users_raw = await _immich_get("api/users")
    if not isinstance(users_raw, list):
        raise HTTPException(status_code=502, detail="Unexpected Immich API response for /api/users")

    result: list[UserPhotoStats] = []
    for user in users_raw:
        uid = user.get("id", "")
        photos = user.get("assets", {}).get("photos", 0) if isinstance(user.get("assets"), dict) else 0
        videos = user.get("assets", {}).get("videos", 0) if isinstance(user.get("assets"), dict) else 0
        storage = user.get("quotaUsageInBytes", 0)
        result.append(UserPhotoStats(
            user_id=uid,
            name=user.get("name", ""),
            email=user.get("email", ""),
            photos=photos,
            videos=videos,
            total_assets=photos + videos,
            storage_used_bytes=storage,
            storage_used_gb=round(storage / 1024 ** 3, 2),
        ))

    return UsersPhotoStats(total_users=len(result), users=result)
