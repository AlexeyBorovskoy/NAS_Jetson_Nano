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
* Privacy: TWO separate callsigns, and the boundary is the word you type.
    - TALK_BOT_TRIGGER (e.g. "нас")     → answered from local data.
      Nothing leaves the house. No outbound request is made at all.
    - TALK_BOT_LLM_TRIGGER (e.g. "@бобик") → free-form question, deliberately
      sent out through the redaction gateway (Phase C).
  Keeping them separate means a family member always knows which one they used.

Enable (in config/.env):
    TALK_BOT_ENABLED=true
    # optional:
    TALK_BOT_ROOM=37pcobmf
    TALK_BOT_TRIGGER=нас
    TALK_BOT_DISPLAY_NAME=NAS Bot
    # Phase C — free-form questions to the provider (empty = off):
    TALK_BOT_LLM_TRIGGER=@бобик
    TALK_BOT_LLM_DISPLAY_NAME=Бобик

Status endpoint: GET /v1/talk/bot/status
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from urllib.parse import quote

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
    # Phase C counters — how much actually left the house today.
    "llm_enabled": False,
    "llm_trigger": "",
    "llm_replied": 0,
    "llm_refused": 0,
    "llm_day": "",
    "llm_day_replies": 0,
    "llm_last_error": None,
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
    lines = [
        "🤖 **NAS Bot** — доступные команды:",
        "- `ping` / `пинг` — проверка связи",
        "- `статус` / `status` — RAM, нагрузка, температура, контейнеры",
        "- `диск` / `disk` — SSD и резервные копии",
        "- `фото` / `photos` — статистика Immich",
        "- `помощь` / `help` — этот список",
        "",
        "🔒 Эти команды считаются **дома**, наружу ничего не уходит.",
    ]
    callsign = settings.talk_bot_llm_trigger.strip()
    if callsign:
        lines += [
            "",
            f"🐕 **{settings.talk_bot_llm_display_name}** — свободные вопросы: `{callsign} <вопрос>`",
            f"   Например: `{callsign} что приготовить из курицы и риса?`",
            "   ⚠️ Такой вопрос **уходит наружу** — в облачную модель, "
            "после вырезания имён, телефонов и почты.",
        ]
    return "\n".join(lines)


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


def _match_llm(text: str) -> str | None:
    """Return the question if the message calls the LLM callsign, else None.

    The callsign must match EXACTLY as configured and stand as the first token.
    Matching is case-insensitive ("@Бобик" works), but the bare name without the
    configured prefix does NOT match.

    Why so strict: this is the one path that leaves the house. A loose match
    means "Бобик хороший пёс" would ship a family message to the provider that
    nobody meant to send — which defeats the whole point of an explicit
    callsign. Verified by test; the bare-name fallback was removed because of it.
    Returns None when the callsign is present but nothing was actually asked.
    """
    callsign = settings.talk_bot_llm_trigger.strip().lower()
    if not callsign:
        return None
    text = (text or "").strip()
    if not text:
        return None

    if not text.lower().startswith(callsign):
        return None
    question = text[len(callsign):]
    # The callsign must be a standalone token: "@бобиков" is not "@бобик".
    if question and question[0].isalnum():
        return None
    # Allow "@бобик, что..." and "@бобик: что..."
    question = question.lstrip(" ,:—-\t")
    return question.strip() or None


def _llm_quota_left(user: str) -> bool:
    """Per-person reply cap at bot level. The gateway enforces the token budget."""
    limit = settings.talk_bot_llm_daily_replies
    today = time.strftime("%Y-%m-%d")
    if _STATE.get("llm_day") != today:
        _STATE["llm_day"] = today
        _STATE["llm_day_replies"] = 0
        _STATE["llm_by_user"] = {}
    if limit <= 0:
        return True
    used = _STATE.setdefault("llm_by_user", {}).get(user, 0)
    return used < limit


def _count_llm_reply(user: str) -> None:
    _STATE["llm_replied"] = _STATE.get("llm_replied", 0) + 1
    _STATE["llm_day_replies"] = _STATE.get("llm_day_replies", 0) + 1
    by_user = _STATE.setdefault("llm_by_user", {})
    by_user[user] = by_user.get(user, 0) + 1


async def _ask_llm(question: str, user: str) -> str:
    """Send a free-form question through the redaction gateway.

    This is the ONLY place in the bot that talks to the outside world. It goes
    through the gateway rather than the provider directly, so redaction and the
    budget cannot be bypassed by this caller.
    """
    if len(question) > settings.talk_bot_llm_max_chars:
        question = question[: settings.talk_bot_llm_max_chars]

    payload = {
        "task": "family_chat_question",
        "prompt": question,
        "mode": "safe",
        # Who asked — the gateway bills and rate-limits per person.
        "user": user,
    }
    async with httpx.AsyncClient(timeout=settings.talk_bot_llm_timeout) as client:
        r = await client.post(settings.talk_bot_llm_url, json=payload)

    if r.status_code == 429:
        _STATE["llm_refused"] = _STATE.get("llm_refused", 0) + 1
        detail = ""
        try:
            detail = (r.json() or {}).get("detail", "")
        except Exception:
            pass
        if "personal daily limit" in detail:
            return "🐕 У тебя закончился дневной лимит вопросов. Продолжим завтра."
        return "🐕 Общий лимит на сегодня исчерпан. Спросите завтра."
    if r.status_code != 200:
        _STATE["llm_last_error"] = f"HTTP {r.status_code}"
        return f"🐕 Не смог спросить — шлюз ответил {r.status_code}."

    data = r.json()
    content = (data.get("content") or "").strip()
    if not content:
        return "🐕 Ответ пришёл пустым."
    return f"🐕 {content}"


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


def _actor(m: dict) -> str:
    """Who wrote the message. actorId is stable; display name is a fallback."""
    return (m.get("actorId") or m.get("actorDisplayName") or "unknown").strip() or "unknown"


async def _handle_messages(token: str, messages: list[dict]) -> None:
    for m in messages:
        _STATE["processed"] += 1
        # Skip system messages (joins, calls, etc.) — only real comments.
        if m.get("systemMessage"):
            continue
        if m.get("messageType") not in (None, "", "comment"):
            continue

        text = m.get("message", "")

        # 1) Local command — answered from local data, nothing leaves the house.
        handler = _match_command(text)
        if handler:
            try:
                reply = await _dispatch(handler)
            except Exception as exc:  # never let one bad command kill the loop
                log.exception("talk bot handler '%s' failed", handler)
                reply = f"⚠️ Ошибка при выполнении команды: {exc}"
            await _send(token, reply, settings.talk_bot_display_name)
            _STATE["replied"] += 1
            log.info(
                "talk bot replied to '%s'",
                handler,
                extra={"fields": {"room": token, "command": handler, "outbound": False}},
            )
            continue

        # 2) LLM callsign — the family explicitly asked to go outside.
        question = _match_llm(text)
        if question:
            user = _actor(m)
            if not _llm_quota_left(user):
                _STATE["llm_refused"] = _STATE.get("llm_refused", 0) + 1
                await _send(
                    token,
                    "🐕 На сегодня лимит вопросов исчерпан.",
                    settings.talk_bot_llm_display_name,
                )
                continue
            if _image_attachment(m):
                await _handle_image_request(token, m, question, user)
                continue
            try:
                reply = await _ask_llm(question, user)
            except Exception as exc:
                log.exception("talk bot LLM call failed")
                _STATE["llm_last_error"] = str(exc)
                reply = "🐕 Не смог получить ответ — попробуйте позже."
            await _send(token, reply, settings.talk_bot_llm_display_name)
            _count_llm_reply(user)
            log.info(
                "talk bot LLM replied",
                extra={"fields": {"room": token, "user": user,
                                  "chars": len(question), "outbound": True}},
            )


def _image_attachment(m: dict) -> dict | None:
    """The image shared with this message, if any (Talk puts it in parameters)."""
    for value in (m.get("messageParameters") or {}).values():
        if value.get("type") == "file" and str(value.get("mimetype", "")).startswith("image/"):
            return value
    return None


def _dav_url(user: str, path: str) -> str:
    base = settings.nextcloud_internal_url.rstrip("/")
    return f"{base}/remote.php/dav/files/{user}/{quote(path)}"


async def _download_attachment(actor: str, path: str) -> bytes:
    """Fetch a Talk attachment over WebDAV.

    Talk stores a shared file under the SENDER's own `Talk/` folder, so the path
    is resolved against that user. The bot authenticates as admin, which can read
    its own uploads; for another user's file this returns 404 and we say so
    plainly instead of pretending the photo was processed.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get(_dav_url(actor, path), auth=_admin_auth())
    if r.status_code != 200:
        raise RuntimeError(f"WebDAV {r.status_code} для {actor}/{path}")
    return r.content


async def _share_image_to_room(token: str, data: bytes, filename: str) -> None:
    """Upload the result and share it into the conversation."""
    admin_user = settings.nextcloud_admin_user
    remote_path = f"Talk/{filename}"
    async with httpx.AsyncClient(timeout=180.0) as client:
        put = await client.put(
            _dav_url(admin_user, remote_path),
            auth=_admin_auth(),
            content=data,
            headers={"Content-Type": "image/jpeg"},
        )
        if put.status_code not in (200, 201, 204):
            raise RuntimeError(f"WebDAV PUT {put.status_code}")
        share = await client.post(
            f"{settings.nextcloud_internal_url.rstrip('/')}"
            "/ocs/v2.php/apps/files_sharing/api/v1/shares",
            auth=_admin_auth(),
            headers=_OCS_HEADERS,
            data={"shareType": 10, "shareWith": token, "path": f"/{remote_path}"},
        )
        if share.status_code not in (200, 201):
            raise RuntimeError(f"share {share.status_code}: {share.text[:150]}")


async def _handle_image_request(token: str, m: dict, question: str, user: str) -> None:
    """Photo + instruction → processed photo back into the same chat."""
    att = _image_attachment(m)
    await _send(
        token,
        "🐕 Рисую новую картинку по мотивам фото, это займёт около минуты. ⚠️ Это НЕ обработка вашего снимка: провайдер не умеет редактировать фотографии. Он посмотрит на фото, опишет его словами и нарисует НОВОЕ изображение по описанию — лица и фон будут другими.",
        settings.talk_bot_llm_display_name,
    )
    try:
        raw = await _download_attachment(user, att.get("path", ""))
    except Exception as exc:
        log.warning("talk bot cannot fetch attachment: %s", exc)
        await _send(token,
                    "🐕 Не смог забрать фотографию из чата. "
                    "Пока умею работать только с теми, что прислали из этой учётной записи.",
                    settings.talk_bot_llm_display_name)
        return

    payload = {
        "image_base64": base64.b64encode(raw).decode("ascii"),
        "filename": att.get("name", "photo.jpg"),
        "instruction": question,
        "user": user,
    }
    url = settings.talk_bot_llm_url.replace("/v1/chat", "/v1/image/edit")
    try:
        async with httpx.AsyncClient(timeout=settings.talk_bot_image_timeout) as client:
            r = await client.post(url, json=payload)
    except Exception as exc:
        log.exception("talk bot image call failed")
        _STATE["llm_last_error"] = str(exc)
        await _send(token, "🐕 Не получилось обработать фотографию.",
                    settings.talk_bot_llm_display_name)
        return

    if r.status_code == 422:
        detail = ""
        try:
            detail = (r.json() or {}).get("detail", "")
        except Exception:
            pass
        await _send(token, f"🐕 {detail}", settings.talk_bot_llm_display_name)
        return
    if r.status_code == 403:
        await _send(token,
                    "🐕 Обработка фотографий выключена в настройках "
                    "(LLM_ALLOW_IMAGE_ANALYSIS=false) — фото не покидают дом.",
                    settings.talk_bot_llm_display_name)
        return
    if r.status_code == 429:
        await _send(token, "🐕 Лимит на сегодня исчерпан.", settings.talk_bot_llm_display_name)
        return
    if r.status_code != 200:
        await _send(token, f"🐕 Шлюз ответил {r.status_code}.", settings.talk_bot_llm_display_name)
        return

    data = r.json()
    img = data.get("image_base64")
    if not img:
        await _send(token, "🐕 Ответ пришёл без картинки.", settings.talk_bot_llm_display_name)
        return
    try:
        await _share_image_to_room(
            token, base64.b64decode(img), f"bobik_{int(time.time())}.jpg"
        )
        _count_llm_reply(user)
    except Exception as exc:
        log.exception("talk bot cannot share result")
        await _send(token, f"🐕 Картинка готова, но не смог отправить её в чат: {exc}",
                    settings.talk_bot_llm_display_name)


async def _send(token: str, message: str, display_name: str) -> None:
    """Post a reply, swallowing transport errors so the loop survives.

    Posts FORM-ENCODED, not JSON. The shared `_ocs_post` helper sends `json=`,
    which Nextcloud OCS rejects with HTTP 404 / statuscode 998 "Invalid query" —
    that is why this bot counted `processed` but never `replied` since Phase A.
    Verified against the live server: `-d "message=..."` works, JSON does not.
    """
    url = f"{settings.nextcloud_internal_url.rstrip('/')}/ocs/v2.php/apps/spreed/api/v1/chat/{token}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                url,
                auth=_admin_auth(),
                headers=_OCS_HEADERS,
                data={"message": message, "actorDisplayName": display_name},
            )
        if r.status_code not in (200, 201):
            log.warning("talk bot send → HTTP %d: %s", r.status_code, r.text[:200])
    except Exception:
        log.exception("talk bot failed to send reply")


def _room_tokens() -> list[str]:
    """Rooms to listen to. Several = each family member gets a private chat."""
    rooms = [t for t in settings.talk_bot_rooms.split() if t]
    if rooms:
        return rooms
    return [settings.talk_bot_room or settings.talk_family_room]


async def _room_loop(token: str) -> None:
    """Long-poll one room forever. One task per room."""
    try:
        last_id = await _fetch_baseline_id(token)
    except Exception as exc:
        log.warning("talk bot baseline failed for %s (%s), starting from 0", token, exc)
        last_id = 0
    _STATE.setdefault("rooms", {})[token] = {"last_message_id": last_id, "error": None}

    while True:
        try:
            messages, last_id = await _poll_once(token, last_id)
            _STATE["rooms"][token] = {"last_message_id": last_id, "error": None}
            _STATE["last_message_id"] = last_id
            _STATE["last_error"] = None
            if messages:
                await _handle_messages(token, messages)
        except asyncio.CancelledError:
            log.info("talk bot loop cancelled for room %s", token)
            raise
        except Exception as exc:
            _STATE["rooms"][token] = {"last_message_id": last_id, "error": str(exc)}
            _STATE["last_error"] = str(exc)
            log.warning("talk bot loop error in room %s: %s", token, exc)
            await asyncio.sleep(10)  # back off on transient failures


async def run_bot_loop() -> None:
    """Background task: poll every configured room in parallel."""
    rooms = _room_tokens()
    callsign = settings.talk_bot_llm_trigger.strip()
    _STATE.update({
        "enabled": True,
        "running": True,
        "room": rooms[0],
        "rooms": {},
        "room_count": len(rooms),
        "started_at": time.time(),
        "llm_enabled": bool(callsign),
        "llm_trigger": callsign,
        "llm_by_user": {},
    })
    log.info(
        "talk bot started, rooms=%s trigger=%r llm_trigger=%r",
        rooms,
        settings.talk_bot_trigger,
        callsign or None,
    )

    try:
        await asyncio.gather(*(_room_loop(t) for t in rooms))
    except asyncio.CancelledError:
        _STATE["running"] = False
        raise


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
