"""
/v1/talk — Nextcloud Talk integration.

Endpoints:
  GET  /v1/talk/rooms          — list all Talk rooms (name, token, participants)
  GET  /v1/talk/rooms/{token}  — room detail with participant list
  POST /v1/talk/notify         — send message to a room (JWT required)

Uses Nextcloud OCS Talk API with admin credentials from config.
Rooms are v4; chat is v1 — see _talk_url().
Admin creds: NEXTCLOUD_ADMIN_USER / NEXTCLOUD_ADMIN_PASSWORD env vars.
"""
from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.routers.auth import require_auth

log = logging.getLogger("nas_jetson_nano_api.talk")
router = APIRouter(prefix="/v1/talk", tags=["Talk — Чат"])

_TALK_BASE = "{nc}/ocs/v2.php/apps/spreed/api/v4"
_OCS_HEADERS = {"OCS-APIRequest": "true", "Accept": "application/json"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _talk_url(path: str, version: str = "v4") -> str:
    """Build an OCS Talk URL.

    ⚠️ Spreed splits its API across versions: rooms live under v4, but **chat is
    only under v1**. Posting a message to the v4 base returns HTTP 404 — which is
    exactly why every chat POST failed until 2026-08-11.
    """
    base = f"{settings.nextcloud_internal_url}/ocs/v2.php/apps/spreed/api/{version}"
    return f"{base}/{path.lstrip('/')}"


def _admin_auth() -> tuple[str, str]:
    if not settings.nextcloud_admin_password:
        raise HTTPException(
            status_code=503,
            detail="NEXTCLOUD_ADMIN_PASSWORD not configured. Set it in .env.",
        )
    return (settings.nextcloud_admin_user, settings.nextcloud_admin_password)


async def _ocs_get(path: str) -> dict:
    auth = _admin_auth()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(_talk_url(path), auth=auth, headers=_OCS_HEADERS)
    if r.status_code not in (200, 201):
        log.warning("Talk OCS GET %s → %d", path, r.status_code)
        raise HTTPException(status_code=502, detail=f"Nextcloud Talk API error: HTTP {r.status_code}")
    return r.json()


async def _ocs_post(path: str, body: dict, version: str = "v4") -> dict:
    """POST to the OCS API.

    ⚠️ Sends FORM data, not JSON. Nextcloud OCS rejects a JSON body with
    HTTP 404 / statuscode 998 "Invalid query". This helper used `json=` and so
    every POST through it silently failed: the Talk bot never delivered a single
    reply, and `POST /v1/talk/notify` — the documented way to raise system alerts
    into the family chat — never worked either. Verified against the live server.
    """
    auth = _admin_auth()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(_talk_url(path, version), auth=auth, headers=_OCS_HEADERS, data=body)
    if r.status_code not in (200, 201):
        log.warning("Talk OCS POST %s → %d: %s", path, r.status_code, r.text[:200])
        raise HTTPException(status_code=502, detail=f"Nextcloud Talk API error: HTTP {r.status_code}")
    return r.json()


# ── Pydantic models ────────────────────────────────────────────────────────────

class RoomSummary(BaseModel):
    token: str
    name: str
    type: int = Field(description="1=one-to-one, 2=group, 3=public, 4=changelog")
    participants: int
    has_call: bool
    last_activity: int = Field(description="Unix timestamp of last message")


class RoomsResponse(BaseModel):
    total: int
    rooms: list[RoomSummary]


class Participant(BaseModel):
    actor_id: str
    display_name: str
    participant_type: int = Field(description="1=owner, 2=moderator, 3=user, 4=guest")
    session_ids: int = Field(description="Number of active sessions (0 = offline)")


class RoomDetail(BaseModel):
    token: str
    name: str
    type: int
    description: str
    participants: list[Participant]
    has_call: bool
    last_activity: int


class NotifyRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Текст сообщения. Поддерживает Markdown.",
        examples=["⚠️ SSD заполнен на 90%! Освободите место."],
    )
    room_token: str = Field(
        default="",
        description=(
            "Токен комнаты Talk. Если не указан — используется семейная группа "
            f"(TALK_FAMILY_ROOM, сейчас: `{settings.talk_family_room}`)."
        ),
        examples=["37pcobmf"],
    )


class NotifyResponse(BaseModel):
    sent: bool
    room_token: str
    room_name: str
    message_id: int


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/rooms",
    response_model=RoomsResponse,
    summary="Список комнат Talk",
    description=(
        "Возвращает все комнаты Nextcloud Talk (группы, личные чаты, системные). "
        "Данные запрашиваются через OCS API с правами администратора. "
        "Семейная группа «Семья» имеет токен `37pcobmf`."
    ),
)
async def list_rooms():
    data = await _ocs_get("room")
    rooms_raw = data.get("ocs", {}).get("data", [])
    rooms = [
        RoomSummary(
            token=r["token"],
            name=r.get("displayName") or r.get("name", ""),
            type=r.get("type", 0),
            participants=r.get("participantCount", 0),
            has_call=r.get("hasCall", False),
            last_activity=r.get("lastActivity", 0),
        )
        for r in rooms_raw
    ]
    log.info("talk rooms listed: %d rooms", len(rooms))
    return RoomsResponse(total=len(rooms), rooms=rooms)


@router.get(
    "/rooms/{token}",
    response_model=RoomDetail,
    summary="Детали комнаты Talk",
    description=(
        "Информация о конкретной комнате: название, описание, список участников с их статусом. "
        "`session_ids > 0` означает что участник сейчас онлайн в чате. "
        "Токен семейной группы: `37pcobmf`."
    ),
)
async def get_room(token: str):
    room_data = await _ocs_get(f"room/{token}")
    r = room_data.get("ocs", {}).get("data", {})

    participants_data = await _ocs_get(f"room/{token}/participants")
    participants_raw = participants_data.get("ocs", {}).get("data", [])

    participants = [
        Participant(
            actor_id=p.get("actorId", ""),
            display_name=p.get("displayName", ""),
            participant_type=p.get("participantType", 3),
            session_ids=len(p.get("sessionIds", [])),
        )
        for p in participants_raw
        if p.get("actorType") == "users"
    ]

    return RoomDetail(
        token=r.get("token", token),
        name=r.get("displayName") or r.get("name", ""),
        type=r.get("type", 0),
        description=r.get("description", ""),
        participants=participants,
        has_call=r.get("hasCall", False),
        last_activity=r.get("lastActivity", 0),
    )


@router.post(
    "/notify",
    response_model=NotifyResponse,
    summary="Отправить сообщение в Talk",
    description=(
        "Отправляет сообщение от имени администратора в указанную комнату Talk. "
        "Если `room_token` не указан — сообщение уходит в семейную группу «Семья». "
        "**Требует JWT.** Используй для системных алертов: заполнение диска, перезапуск контейнера и т.д. "
        "Сообщение видят все участники комнаты в приложении Nextcloud Talk."
    ),
    status_code=201,
)
async def notify(
    body: NotifyRequest,
    _username: Annotated[str, Depends(require_auth)],
):
    room_token = body.room_token or settings.talk_family_room

    # Get room name for response
    try:
        room_data = await _ocs_get(f"room/{room_token}")
        room_name = room_data.get("ocs", {}).get("data", {}).get("displayName", room_token)
    except HTTPException:
        room_name = room_token

    # Send message via Talk chat API
    # chat lives under v1 only — see _talk_url()
    result = await _ocs_post(
        f"chat/{room_token}",
        {"message": body.message, "actorDisplayName": "NAS_Jetson_Nano API"},
        version="v1",
    )
    ocs_data = result.get("ocs", {}).get("data", {})
    msg_id = ocs_data.get("id", 0)

    log.info(
        "talk notify sent by %s to room %s: msg_id=%d",
        _username, room_token, msg_id,
        extra={"fields": {"room": room_token, "sender": _username, "msg_id": msg_id}},
    )
    return NotifyResponse(
        sent=True,
        room_token=room_token,
        room_name=room_name,
        message_id=msg_id,
    )
