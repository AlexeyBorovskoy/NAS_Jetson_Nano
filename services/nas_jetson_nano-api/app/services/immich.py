"""
Клиент Immich Admin API (чтение статистики фотоархива семьи).

Вынесено из app/routers/photos.py (CQ-02, docs/audit/2026-10-02_code_audit/REPORT.ru.md
§4, §6): раньше app/routers/talk_bot.py звал `photos_mod._immich_get` напрямую как
приватную функцию чужого роутера — переименование в photos.py молча ломало бы ответ
«фото» у Talk-бота. Логика не менялась, только место и имя верхнего уровня (без
ведущего `_`).
"""
from __future__ import annotations

import httpx
from fastapi import HTTPException

from app.config import settings


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


async def immich_get(path: str) -> dict | list:
    headers = _immich_headers()
    url = f"{settings.immich_internal_url}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Immich API key invalid or expired")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Immich API error: HTTP {r.status_code}")
    return r.json()
