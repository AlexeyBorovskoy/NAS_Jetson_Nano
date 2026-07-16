"""
/v1/users — Family user management via Nextcloud OCS API.

Endpoints:
  GET  /v1/users                    — list all Nextcloud users
  GET  /v1/users/{username}         — user detail: quota, storage, last seen
  POST /v1/users/{username}/notify  — send Talk DM to user (JWT required)

All endpoints require JWT. Uses Nextcloud OCS API v1 with admin credentials.
"""
from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.routers.auth import require_auth

log = logging.getLogger("nas_jetson_nano_api.users")
router = APIRouter(prefix="/v1/users", tags=["Пользователи"])

_OCS_HEADERS = {"OCS-APIRequest": "true", "Accept": "application/json"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _nc_url(path: str) -> str:
    return f"{settings.nextcloud_internal_url}/{path.lstrip('/')}"


def _admin_auth() -> tuple[str, str]:
    if not settings.nextcloud_admin_password:
        raise HTTPException(
            status_code=503,
            detail="NEXTCLOUD_ADMIN_PASSWORD not configured. Set it in .env.",
        )
    return (settings.nextcloud_admin_user, settings.nextcloud_admin_password)


async def _nc_get(path: str) -> dict:
    auth = _admin_auth()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(_nc_url(path), auth=auth, headers=_OCS_HEADERS)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Nextcloud OCS error: HTTP {r.status_code}")
    return r.json()


async def _nc_post(path: str, body: dict) -> dict:
    auth = _admin_auth()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(_nc_url(path), auth=auth, headers=_OCS_HEADERS, json=body)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Nextcloud OCS error: HTTP {r.status_code}")
    return r.json()


# ── Pydantic models ────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    username: str
    display_name: str
    enabled: bool
    groups: list[str]
    last_login: int = Field(description="Unix timestamp, 0 if never logged in")


class UsersResponse(BaseModel):
    total: int
    users: list[UserSummary]


class StorageInfo(BaseModel):
    used_bytes: int
    free_bytes: int
    total_bytes: int
    used_pct: float
    quota: str = Field(description="'none' if unlimited")


class UserDetail(BaseModel):
    username: str
    display_name: str
    email: str
    enabled: bool
    groups: list[str]
    last_login: int
    storage: StorageInfo


class NotifyDMRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Текст личного сообщения пользователю.",
        examples=["Привет! Твои фото загрузились на сервер."],
    )


class NotifyDMResponse(BaseModel):
    sent: bool
    to_user: str
    room_token: str
    message_id: int


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=UsersResponse,
    summary="Список пользователей семейного облака",
    description=(
        "Возвращает всех пользователей Nextcloud: имя, группы, время последнего входа. "
        "`last_login = 0` означает что пользователь ни разу не входил. "
        "**Требует JWT.**"
    ),
)
async def list_users(_: Annotated[str, Depends(require_auth)]):
    data = await _nc_get("ocs/v1.php/cloud/users?limit=100")
    usernames: list[str] = data.get("ocs", {}).get("data", {}).get("users", [])

    users: list[UserSummary] = []
    for uname in usernames:
        try:
            udata = await _nc_get(f"ocs/v1.php/cloud/users/{uname}")
            ud = udata.get("ocs", {}).get("data", {})
            users.append(UserSummary(
                username=uname,
                display_name=ud.get("displayname", uname),
                enabled=ud.get("enabled", True),
                groups=ud.get("groups", []),
                last_login=ud.get("lastLogin", 0),
            ))
        except HTTPException:
            log.warning("could not fetch user detail for %s", uname)

    log.info("users listed: %d", len(users))
    return UsersResponse(total=len(users), users=users)


@router.get(
    "/{username}",
    response_model=UserDetail,
    summary="Детали пользователя",
    description=(
        "Полная информация о пользователе: квота, использование диска, email, группы, "
        "время последнего входа. **Требует JWT.**"
    ),
)
async def get_user(username: str, _: Annotated[str, Depends(require_auth)]):
    data = await _nc_get(f"ocs/v1.php/cloud/users/{username}")
    ud = data.get("ocs", {}).get("data", {})
    if not ud:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    quota_raw = ud.get("quota", {})
    used = quota_raw.get("used", 0) if isinstance(quota_raw, dict) else 0
    total = quota_raw.get("total", 0) if isinstance(quota_raw, dict) else 0
    free = quota_raw.get("free", 0) if isinstance(quota_raw, dict) else 0
    used_pct = round(used / total * 100, 1) if total > 0 else 0.0
    quota_str = str(quota_raw.get("quota", "none")) if isinstance(quota_raw, dict) else "none"

    return UserDetail(
        username=username,
        display_name=ud.get("displayname", username),
        email=ud.get("email", ""),
        enabled=ud.get("enabled", True),
        groups=ud.get("groups", []),
        last_login=ud.get("lastLogin", 0),
        storage=StorageInfo(
            used_bytes=used,
            free_bytes=free,
            total_bytes=total,
            used_pct=used_pct,
            quota=quota_str,
        ),
    )


@router.post(
    "/{username}/notify",
    response_model=NotifyDMResponse,
    summary="Отправить личное сообщение пользователю",
    description=(
        "Создаёт или открывает существующий приватный чат с пользователем "
        "и отправляет ему личное сообщение через Nextcloud Talk. "
        "**Требует JWT.** Пользователь должен быть зарегистрирован в Nextcloud."
    ),
    status_code=201,
)
async def notify_user(
    username: str,
    body: NotifyDMRequest,
    sender: Annotated[str, Depends(require_auth)],
):
    # Create or get 1-to-1 room
    room_result = await _nc_post(
        "ocs/v2.php/apps/spreed/api/v4/room",
        {"roomType": 1, "invite": username},
    )
    room_data = room_result.get("ocs", {}).get("data", {})
    room_token = room_data.get("token", "")
    if not room_token:
        raise HTTPException(status_code=502, detail="Could not create Talk room for DM")

    # Send message
    msg_result = await _nc_post(
        f"ocs/v2.php/apps/spreed/api/v4/chat/{room_token}",
        {"message": body.message},
    )
    msg_data = msg_result.get("ocs", {}).get("data", {})
    msg_id = msg_data.get("id", 0)

    log.info(
        "DM sent by %s to %s: msg_id=%d room=%s",
        sender, username, msg_id, room_token,
        extra={"fields": {"sender": sender, "to": username, "room": room_token}},
    )
    return NotifyDMResponse(
        sent=True,
        to_user=username,
        room_token=room_token,
        message_id=msg_id,
    )
