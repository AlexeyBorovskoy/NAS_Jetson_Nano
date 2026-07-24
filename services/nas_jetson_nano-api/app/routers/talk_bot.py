"""
Talk AI bot — Phase A (polling).

A background task long-polls the family Nextcloud Talk room and answers a small
set of commands by reusing the existing read-only helpers (system / storage /
photos). Replies are sent through the proven admin-OCS path from `talk.py`.

Design notes
------------
* Opt-in: only runs when TALK_BOT_ENABLED=true. Default behaviour of the API is
  unchanged, so deploying this code alone is safe.
* Version-agnostic: uses the admin OCS chat API (v1 read, v4 send via talk.py),
  so it does NOT depend on the Nextcloud Talk Bot (webhook) feature.
* Loop-safe: only messages whose FIRST word is a known command are handled, and
  every reply starts with an emoji, so the bot never reacts to its own replies.
* Privacy: every command here answers from local data only — nothing is sent to
  any external LLM. Free-form Q&A (via the redaction gateway) is Phase C.

Enable (in config/.env):
    TALK_BOT_ENABLED=true
    # optional:
    TALK_BOT_ROOM=37pcobmf
    TALK_BOT_TRIGGER=нас
    TALK_BOT_DISPLAY_NAME=NAS Bot

Status endpoint: GET /v1/talk/bot/status
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import photos as photos_mod
from app.routers import storage as storage_mod
from app.routers import system as system_mod
from app.routers.talk import _OCS_HEADERS, _admin_auth, _ocs_post

log = logging.getLogger("nas_jetson_nano_api.talk_bot")
router = APIRouter(prefix="/v1/talk/bot", tags=["Talk — Чат"])

# Module-level state, surfaced via GET /v1/talk/bot/status
_STATE: dict = {
    "enabled": False,
    "running": False,
    "room": "",
    "last_message_id": 0,
    "processed": 0,
    "replied": 0,
    "last_error": None,
    "started_at": None,
}

# command keyword (first word, lowercased) -> handler name
_COMMANDS = {
    "ping": "ping", "пинг": "ping",
    "status": "status", "статус": "status", "стат": "status",
    "disk": "disk", "диск": "disk", "storage": "disk", "хранилище": "disk", "место": "disk",
    "photos": "photos", "фото": "photos", "immich": "photos",
    "help": "help", "помощь": "help", "команды": "help",
}


# ── Formatting helpers ──────────────────────────────────────────────────────────

def _fmt_uptime(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _build_help() -> str:
    return (
        "🤖 **NAS Bot** — доступные команды:\n"
        "- `ping` / `пинг` — проверка связи\n"
        "- `статус` / `status` — RAM, нагрузка, температура, контейнеры\n"
        "- `диск` / `disk` — SSD и резервные копии\n"
        "- `фото` / `photos` — статистика Immich\n"
        "- `помощь` / `help` — этот список"
    )


async def _build_status() -> str:
    ram = system_mod._read_meminfo()
    load = system_mod._read_loadavg()
    up = system_mod._read_uptime_seconds()
    thermal = system_mod._read_thermal()
    cpu_t = next((z["temp_c"] for z in thermal if z["zone"] == "CPU-therm"), None)

    expected = set(settings.expected_containers.split())
    containers = await system_mod._docker_ps_json()
    running = sum(1 for c in containers if c.get("state", "").lower() == "running")
    unhealthy = [
        c.get("name", "")
        for c in containers
        if c.get("name") in expected and c.get("state", "").lower() != "running"
    ]

    lines = [
        "📊 **Статус Jetson Nano**",
        f"- RAM: {ram.get('used_mb', 0)}/{ram.get('total_mb', 0)} MB ({ram.get('used_pct', 0)}%)",
        f"- Load (1/5/15m): {load.get('1m', '?')} / {load.get('5m', '?')} / {load.get('15m', '?')}",
        f"- Uptime: {_fmt_uptime(up)}",
    ]
    if cpu_t is not None:
        lines.append(f"- CPU temp: {cpu_t}°C")
    lines.append(f"- Контейнеры: {running} running")
    if unhealthy:
        lines.append(f"- ⚠️ Не запущены: {', '.join(unhealthy)}")
    else:
        lines.append("- ✅ Все ожидаемые контейнеры работают")
    return "\n".join(lines)


def _build_disk() -> str:
    ssd = storage_mod._disk_info(storage_mod.STORAGE_ROOT)
    if not ssd.get("mounted"):
        return "💾 **Хранилище**\n- ⚠️ SSD `/mnt/storage` не смонтирован!"

    lines = [
        "💾 **Хранилище (SSD)**",
        f"- Использовано: {ssd.get('used_gb', 0)}/{ssd.get('total_gb', 0)} GB ({ssd.get('used_pct', 0)}%)",
        f"- Свободно: {ssd.get('free_gb', 0)} GB",
    ]
    backups = storage_mod._backup_info()
    if backups.get("available"):
        for d in backups.get("dumps", []):
            if d.get("file"):
                age = d.get("age_hours")
                age_txt = f"{age}ч назад" if age is not None else "—"
                lines.append(f"- Бэкап {d['db']}: {d.get('size_mb', 0)} MB, {age_txt}")
            else:
                lines.append(f"- Бэкап {d['db']}: ⚠️ нет дампа")
    return "\n".join(lines)


async def _build_photos() -> str:
    try:
        stats = await photos_mod._immich_get("api/server/statistics")
    except Exception:
        return (
            "📷 **Immich**\n- ⚠️ Недоступен или `IMMICH_API_KEY` не настроен."
        )
    photos = stats.get("photos", 0)
    videos = stats.get("videos", 0)
    usage_gb = round(stats.get("usage", 0) / 1024 ** 3, 2)
    lines = [
        "📷 **Фотоархив Immich**",
        f"- Фото: {photos}",
        f"- Видео: {videos}",
        f"- Занято: {usage_gb} GB",
    ]
    try:
        albums = await photos_mod._immich_get("api/albums")
        if isinstance(albums, list):
            lines.append(f"- Альбомы: {len(albums)}")
    except Exception:
        pass
    return "\n".join(lines)


async def _dispatch(handler: str) -> str:
    if handler == "ping":
        return f"🏓 pong · uptime {_fmt_uptime(system_mod._read_uptime_seconds())}"
    if handler == "status":
        return await _build_status()
    if handler == "disk":
        return _build_disk()
    if handler == "photos":
        return await _build_photos()
    return _build_help()


# ── Message parsing ─────────────────────────────────────────────────────────────

def _match_command(text: str) -> str | None:
    """Return handler name if the message is a command for us, else None."""
    text = (text or "").strip()
    if not text:
        return None
    trigger = settings.talk_bot_trigger.strip().lower()
    if trigger:
        low = text.lower()
        if not low.startswith(trigger):
            return None
        text = text[len(trigger):].strip()
    first = text.split()[0].lower() if text.split() else ""
    return _COMMANDS.get(first)


# ── OCS chat polling ─────────────────────────────────────────────────────────────

def _chat_url(token: str) -> str:
    base = settings.nextcloud_internal_url.rstrip("/")
    return f"{base}/ocs/v2.php/apps/spreed/api/v1/chat/{token}"


async def _fetch_baseline_id(token: str) -> int:
    """Latest message id in the room, so we don't replay history on startup."""
    params = {"lookIntoFuture": 0, "limit": 1, "setReadMarker": 0}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(_chat_url(token), auth=_admin_auth(), headers=_OCS_HEADERS, params=params)
    if r.status_code == 200:
        data = r.json().get("ocs", {}).get("data", [])
        if data:
            return max(int(m.get("id", 0)) for m in data)
    last_given = r.headers.get("x-chat-last-given")
    return int(last_given) if last_given else 0


async def _poll_once(token: str, last_id: int) -> tuple[list[dict], int]:
    """Long-poll for messages newer than last_id. Returns (messages, new_last_id)."""
    params = {
        "lookIntoFuture": 1,
        "lastKnownMessageId": last_id,
        "timeout": settings.talk_bot_poll_timeout,
        "limit": 100,
        "setReadMarker": 0,
        "includeLastKnown": 0,
    }
    client_timeout = settings.talk_bot_poll_timeout + 15
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        r = await client.get(_chat_url(token), auth=_admin_auth(), headers=_OCS_HEADERS, params=params)

    if r.status_code == 304:  # no new messages within the long-poll window
        return [], last_id
    if r.status_code != 200:
        log.warning("talk bot poll HTTP %d: %s", r.status_code, r.text[:200])
        return [], last_id

    messages = r.json().get("ocs", {}).get("data", [])
    new_last = last_id
    header_last = r.headers.get("x-chat-last-given")
    if header_last:
        new_last = max(new_last, int(header_last))
    for m in messages:
        new_last = max(new_last, int(m.get("id", 0)))
    return messages, new_last


async def _handle_messages(token: str, messages: list[dict]) -> None:
    for m in messages:
        _STATE["processed"] += 1
        # Skip system messages (joins, calls, etc.) — only real comments.
        if m.get("systemMessage"):
            continue
        if m.get("messageType") not in (None, "", "comment"):
            continue
        handler = _match_command(m.get("message", ""))
        if not handler:
            continue
        try:
            reply = await _dispatch(handler)
        except Exception as exc:  # never let one bad command kill the loop
            log.exception("talk bot handler '%s' failed", handler)
            reply = f"⚠️ Ошибка при выполнении команды: {exc}"
        try:
            await _ocs_post(
                f"chat/{token}",
                {"message": reply, "actorDisplayName": settings.talk_bot_display_name},
            )
            _STATE["replied"] += 1
            log.info(
                "talk bot replied to '%s'",
                handler,
                extra={"fields": {"room": token, "command": handler}},
            )
        except Exception:
            log.exception("talk bot failed to send reply")


async def run_bot_loop() -> None:
    """Background task: baseline, then long-poll and answer commands forever."""
    token = settings.talk_bot_room or settings.talk_family_room
    _STATE.update({"enabled": True, "running": True, "room": token, "started_at": time.time()})
    log.info("talk bot started, room=%s trigger=%r", token, settings.talk_bot_trigger)

    # Baseline: start from the latest message so we don't replay old chat.
    try:
        last_id = await _fetch_baseline_id(token)
    except Exception as exc:
        log.warning("talk bot baseline failed (%s), starting from 0", exc)
        last_id = 0
    _STATE["last_message_id"] = last_id

    while True:
        try:
            messages, last_id = await _poll_once(token, last_id)
            _STATE["last_message_id"] = last_id
            _STATE["last_error"] = None
            if messages:
                await _handle_messages(token, messages)
        except asyncio.CancelledError:
            log.info("talk bot loop cancelled")
            _STATE["running"] = False
            raise
        except Exception as exc:
            _STATE["last_error"] = str(exc)
            log.warning("talk bot loop error: %s", exc)
            await asyncio.sleep(10)  # back off on transient failures


@router.get(
    "/status",
    summary="Статус Talk-бота",
    description=(
        "Состояние фонового Talk-бота (Phase A): включён ли, какую комнату слушает, "
        "id последнего обработанного сообщения, счётчики. Без авторизации."
    ),
)
async def bot_status():
    return JSONResponse(content=_STATE)
