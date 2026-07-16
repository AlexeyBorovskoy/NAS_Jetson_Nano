"""
/api/auth — JWT authentication via Nextcloud OCS API.

Flow:
  POST /api/auth/login  →  validate credentials against Nextcloud  →  return JWT
  GET  /api/auth/me     →  decode JWT, return user info

Token is Bearer JWT, signed with NAS_JETSON_NANO_API_JWT_SECRET (from env).
TTL: NAS_JETSON_NANO_API_JWT_TTL_HOURS (default 24h).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.auth")
router = APIRouter(prefix="/api/auth", tags=["Авторизация"])
_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


# ── Pydantic models ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str


class UserInfo(BaseModel):
    username: str
    source: str = "nextcloud"


# ── Nextcloud OCS validation ───────────────────────────────────────────────────

async def _validate_nextcloud(username: str, password: str) -> bool:
    """Validate credentials against Nextcloud OCS API."""
    url = f"{settings.nextcloud_internal_url}/ocs/v1.php/cloud/users/{username}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                url,
                auth=(username, password),
                headers={"OCS-APIREQUEST": "true"},
            )
        ok = r.status_code == 200
        log.info("nextcloud auth for %s: %s", username, "OK" if ok else f"HTTP {r.status_code}")
        return ok
    except Exception as exc:
        log.warning("nextcloud auth request failed: %s", exc)
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(username: str) -> tuple[str, int]:
    ttl_seconds = settings.jwt_ttl_hours * 3600
    expire = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    payload = {"sub": username, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, ttl_seconds


def _decode_token(token: str) -> str:
    """Decode JWT and return username, or raise HTTPException."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid or expired: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependency: require valid JWT ─────────────────────────────────────────────

async def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """FastAPI dependency — inject into any route that needs authentication."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход — получить JWT",
    description=(
        "Проверяет логин/пароль через Nextcloud OCS API. "
        "При успехе возвращает Bearer JWT-токен (TTL задаётся `NAS_JETSON_NANO_API_JWT_TTL_HOURS`, по умолчанию 24ч). "
        "Используй токен в заголовке: `Authorization: Bearer <token>`."
    ),
)
async def login(body: LoginRequest):
    valid = await _validate_nextcloud(body.username, body.password)
    if not valid:
        log.warning("failed login attempt for user: %s", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token, ttl = _create_token(body.username)
    log.info("login OK: %s", body.username)
    return TokenResponse(
        access_token=token,
        expires_in=ttl,
        username=body.username,
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Текущий пользователь",
    description="Возвращает информацию о пользователе из JWT-токена. Требует Authorization: Bearer.",
)
async def me(username: Annotated[str, Depends(require_auth)]):
    return UserInfo(username=username)
