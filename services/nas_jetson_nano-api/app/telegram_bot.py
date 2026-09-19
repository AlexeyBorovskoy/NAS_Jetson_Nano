"""Telegram-фронт @бобик: первый срез (закачки + вопросы к GigaChat).

Спецификации: docs/superpowers/specs/2026-09-19-home-downloader-design.md,
docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md.
Jetson напрямую до Telegram не доходит — long polling идёт через SSH SOCKS на VPS
(`TELEGRAM_PROXY=socks5://172.17.0.1:1080`). Обращение — «@бобик …» / «бобик, …»;
всё без обращения в группе отбрасывается без записи в журнал.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import httpx

from app import downloads as downloads_mod
from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.telegram")
# httpx на INFO пишет URL запроса, а в URL Bot API — токен: в журнал его не пускаем.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TORRENT_LIMIT = 20 * 1024 * 1024  # предел Bot API getFile — на сам .torrent, не на закачку
HELP = ("🐕 Я Бобик. Пишите «@бобик» и дальше:\n"
        "• скачай <magnet или ссылка> — скачаю домой, в \\\\192.168.0.50\\hdd2tb\\Downloads\n"
        "• .torrent-файл с подписью «@бобик скачай»\n"
        "• закачки — что качается и сколько места\n"
        "• отмени N — отменить закачку N\n"
        "• любой другой вопрос — отвечу через GigaChat")
STRANGER_TEXT = "🐕 Вы не в семейном списке — я отвечаю только своим."


class TgError(Exception):
    def __init__(self, code: int, description: str = "", retry_after: int = 0):
        super().__init__("telegram %s: %s" % (code, description))
        self.code = code
        self.retry_after = retry_after


class TgApi:
    """Bot API через прокси. Токен живёт только в URL запроса и в журнал не попадает."""

    def __init__(self, token: str, proxy=None, base=None, transport=None):
        self._token = token
        self._base = (base or settings.telegram_api).rstrip("/")
        kw = {"timeout": 45}
        if transport is not None:
            kw["transport"] = transport
        elif proxy:
            kw["proxy"] = proxy
        self._client = httpx.AsyncClient(**kw)

    async def call(self, method: str, **params):
        r = await self._client.post("%s/bot%s/%s" % (self._base, self._token, method), json=params)
        try:
            data = r.json()
        except ValueError:
            raise TgError(r.status_code, "не JSON")
        if not data.get("ok"):
            raise TgError(data.get("error_code", r.status_code), data.get("description", ""),
                          (data.get("parameters") or {}).get("retry_after", 0))
        return data["result"]

    async def file_bytes(self, file_id: str, limit: int = TORRENT_LIMIT) -> bytes:
        info = await self.call("getFile", file_id=file_id)
        if int(info.get("file_size") or 0) > limit:
            raise TgError(413, "файл больше предела")
        r = await self._client.get("%s/file/bot%s/%s" % (self._base, self._token, info["file_path"]))
        if len(r.content) > limit:
            raise TgError(413, "файл больше предела")
        return r.content


def parse_users(s: str) -> dict:
    users = {}
    for part in (s or "").split():
        uid, _, login = part.partition(":")
        if uid.lstrip("-").isdigit() and login:
            users[int(uid)] = login
    return users


def addressed_text(msg: dict, bot_username: str, callsigns: list):
    text = (msg.get("text") or msg.get("caption") or "").strip()
    low = text.lower()
    for cs in list(callsigns) + ["@" + bot_username.lower()]:
        if cs and low.startswith(cs.lower()):
            return text[len(cs):].lstrip(" ,:—-\t")
    reply_from = ((msg.get("reply_to_message") or {}).get("from") or {}).get("username", "")
    if reply_from.lower() == bot_username.lower():
        return text
    if (msg.get("chat") or {}).get("type") == "private":
        return text
    return None


def route(text: str):
    low = (text or "").strip().lower()
    if low.startswith("скачай"):
        return "download", text.strip()[len("скачай"):].strip()
    if low.startswith("закачки"):
        return "list", None
    m = re.match(r"отмени\s+(\d+)", low)
    if m:
        return "cancel", int(m.group(1))
    return "ask", text.strip()


class TelegramBot:
    def __init__(self, api: TgApi, downloads, answer=None, state_path=None):
        self.api = api
        self.downloads = downloads
        if answer is None:
            from app.routers import talk_bot
            answer = talk_bot.answer
        self.answer = answer
        self.state_path = state_path or settings.telegram_state_file
        self.users = parse_users(settings.telegram_users)
        self.family = int(settings.telegram_family_chat_id) if settings.telegram_family_chat_id else None
        self.callsigns = [c.strip() for c in settings.telegram_callsigns.split("|") if c.strip()]
        self.bot_username = ""
        self.state = self._load()

    # ── состояние ─────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.state_path)), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh)
        os.replace(tmp, self.state_path)

    def _owner_chat(self):
        for uid, login in self.users.items():
            if login == settings.telegram_owner_login:
                return uid
        return None

    async def _say(self, chat_id: int, text: str, reply_to=None) -> None:
        params = {"chat_id": chat_id, "text": text}
        if reply_to:
            params["reply_to_message_id"] = reply_to
        await self.api.call("sendMessage", **params)

    # ── обработка ─────────────────────────────────────────────────────────────
    async def handle_update(self, upd: dict) -> None:
        mcm = upd.get("my_chat_member")
        if mcm:
            chat = mcm.get("chat") or {}
            if chat.get("type") in ("group", "supergroup") and chat.get("id") != self.family:
                await self.api.call("leaveChat", chat_id=chat["id"])
            return
        msg = upd.get("message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat.get("type") in ("group", "supergroup") and chat_id != self.family:
            await self.api.call("leaveChat", chat_id=chat_id)
            return
        text = addressed_text(msg, self.bot_username, self.callsigns)
        if text is None:
            return  # не нам: не обрабатываем, не храним, не пишем в журнал
        uid = (msg.get("from") or {}).get("id")
        login = self.users.get(uid)
        if login is None:
            await self._stranger(msg, chat)
            return
        doc = msg.get("document")
        kind, arg = route(text)
        log.info("telegram command", extra={"fields": {
            "user": login, "chat_type": chat.get("type"),
            "kind": "torrent" if doc else kind}})
        mid = msg.get("message_id")
        if text in ("", "/start") or text.startswith("/start@") or text == "/help":
            await self._say(chat_id, HELP)
            return
        if doc and (doc.get("file_name") or "").lower().endswith(".torrent"):
            if kind != "download" and chat.get("type") != "private":
                return
            if int(doc.get("file_size") or 0) > TORRENT_LIMIT:
                await self._say(chat_id, "❌ .torrent-файл больше 20 МБ — пришлите magnet-ссылку.", mid)
                return
            data = await self.api.file_bytes(doc["file_id"])
            await self._say(chat_id, await self.downloads.add_torrent(data, chat_id, login), mid)
            return
        if kind == "download":
            try:
                link = downloads_mod.parse_link(arg)
            except downloads_mod.LinkError as exc:
                await self._say(chat_id, "❌ %s" % exc, mid)
                return
            await self._say(chat_id, await self.downloads.add_link(link, chat_id, login), mid)
        elif kind == "list":
            await self._say(chat_id, await self.downloads.list_text(), mid)
        elif kind == "cancel":
            await self._say(chat_id, await self.downloads.cancel(arg), mid)
        else:
            await self.api.call("sendChatAction", chat_id=chat_id, action="typing")
            await self._say(chat_id, await self.answer(arg, login), mid)

    async def _stranger(self, msg: dict, chat: dict) -> None:
        if chat.get("type") != "private":
            return
        uid = (msg.get("from") or {}).get("id")
        seen = self.state.setdefault("strangers", [])
        if uid in seen:
            return
        seen.append(uid)
        self._save()
        await self._say(chat["id"], STRANGER_TEXT)
        owner = self._owner_chat()
        if owner:
            name = (msg.get("from") or {}).get("first_name", "")
            await self._say(owner, "🐕 Боту написал незнакомый аккаунт: %s (user_id %s). "
                                   "Если это семья — добавьте в TELEGRAM_USERS." % (name, uid))

    # ── циклы ─────────────────────────────────────────────────────────────────
    async def poll_once(self) -> None:
        offset = self.state.get("offset", 0)
        updates = await self.api.call("getUpdates", offset=offset, timeout=30,
                                      allowed_updates=["message", "my_chat_member"])
        for upd in updates:
            try:
                await self.handle_update(upd)
            except Exception:
                log.exception("telegram update failed")
            self.state["offset"] = upd["update_id"] + 1
            self._save()

    async def poll_forever(self) -> None:
        backoff = 1
        while True:
            try:
                await self.poll_once()
                backoff = 1
            except TgError as exc:
                await asyncio.sleep(exc.retry_after or backoff)
                backoff = min(backoff * 2, 60)
            except (httpx.HTTPError, OSError) as exc:
                log.warning("telegram unreachable: %s", type(exc).__name__)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def downloads_once(self) -> None:
        for chat_id, text in await self.downloads.tick():
            await self._say(chat_id, text)

    async def downloads_forever(self, interval: int = 30) -> None:
        while True:
            try:
                await self.downloads_once()
            except Exception:
                log.exception("downloads tick failed")
            await asyncio.sleep(interval)


async def run() -> None:
    api = TgApi(settings.telegram_bot_token, proxy=settings.telegram_proxy or None)
    bot = TelegramBot(api, downloads_mod.Downloads())
    while not bot.bot_username:
        try:
            bot.bot_username = (await api.call("getMe"))["username"]
        except (TgError, httpx.HTTPError, OSError):
            await asyncio.sleep(30)
    await asyncio.gather(bot.poll_forever(), bot.downloads_forever())
