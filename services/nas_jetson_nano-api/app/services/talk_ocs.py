"""
Админ-OCS путь Nextcloud Talk: заголовки, Basic-auth и отправка сообщений (POST).

Вынесено из app/routers/talk.py (CQ-02, docs/audit/2026-10-02_code_audit/REPORT.ru.md
§4, §6): раньше app/routers/talk_bot.py импортировал эти три имени как приватные
(`from app.routers.talk import _OCS_HEADERS, _admin_auth, _ocs_post`) — переименование
внутри роутера молча ломало бы бота. Логика не менялась, только место и имена
верхнего уровня (без ведущего `_`).

`_talk_url` продублирован здесь как приватный хелпер: он нужен только `ocs_post`,
а `_ocs_get`/собственный `_talk_url` в `talk.py` используются GET-путём списка/деталей
комнаты и не были частью находки CQ-02 (не приватные имена, которые звал чужой
модуль) — переносить их не нужно. Обе копии строят URL одинаково и расходиться им
негде.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.services.talk_ocs")

OCS_HEADERS = {"OCS-APIRequest": "true", "Accept": "application/json"}


def _talk_url(path: str, version: str = "v4") -> str:
    base = f"{settings.nextcloud_internal_url}/ocs/v2.php/apps/spreed/api/{version}"
    return f"{base}/{path.lstrip('/')}"


def admin_auth() -> tuple[str, str]:
    if not settings.nextcloud_admin_password:
        raise HTTPException(
            status_code=503,
            detail="NEXTCLOUD_ADMIN_PASSWORD not configured. Set it in .env.",
        )
    return (settings.nextcloud_admin_user, settings.nextcloud_admin_password)


async def ocs_post(path: str, body: dict, version: str = "v4") -> dict:
    """POST to the OCS API.

    ⚠️ Sends FORM data, not JSON. Nextcloud OCS rejects a JSON body with
    HTTP 404 / statuscode 998 "Invalid query". This helper used `json=` and so
    every POST through it silently failed: the Talk bot never delivered a single
    reply, and `POST /v1/talk/notify` — the documented way to raise system alerts
    into the family chat — never worked either. Verified against the live server.
    """
    auth = admin_auth()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(_talk_url(path, version), auth=auth, headers=OCS_HEADERS, data=body)
    if r.status_code not in (200, 201):
        log.warning("Talk OCS POST %s → %d: %s", path, r.status_code, r.text[:200])
        raise HTTPException(status_code=502, detail=f"Nextcloud Talk API error: HTTP {r.status_code}")
    return r.json()
