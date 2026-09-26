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
import time

import httpx

from app import downloads as downloads_mod
from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.telegram")
# httpx на INFO пишет URL запроса, а в URL Bot API — токен: в журнал его не пускаем.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TORRENT_LIMIT = 20 * 1024 * 1024  # предел Bot API getFile — на сам .torrent, не на закачку
HELP = ("🐕 Я Бобик. Обращайтесь по имени — «бобик, …» — и дальше:\n"
        "• скачай <magnet или ссылка> — скачаю домой, в \\\\192.168.0.50\\hdd2tb\\Downloads\n"
        "• .torrent-файл с подписью «@бобик скачай»\n"
        "• закачки — что качается и сколько места\n"
        "• отмени N — отменить закачку N\n"
        "• забудь — начать разговор заново\n"
        "• что сломалось — статус дома (только владельцу)\n"
        "• любой другой вопрос — отвечу через GigaChat")
STRANGER_TEXT = "🐕 Вы не в семейном списке — я отвечаю только своим."
GREETING = "🐕 Гав! Я тут. Спросите что-нибудь или напишите «бобик, закачки»."
# E3: состояние дома — только владельцу, остальным вежливый отказ (не «не понял»).
HEALTH_OWNER_ONLY_TEXT = "🐕 Состояние дома — это к владельцу, не ко всем."
# «что сломалось», «всё/все работает(?)», «как дела/там дома», «как сервер», «статус дома».
_HEALTH_RE = re.compile(
    r"^(что\s+сломалось|"
    r"(?:всё|все)(?:\s+ли)?\s+работает|"
    r"как\s+дела\s+дома|как\s+(?:там\s+)?сервер|"
    r"статус\s+дома|что\s+не\s+так(?:\s+дома)?)\s*\??$",
    re.IGNORECASE,
)
# «бобик» отдельным словом в любой падежной форме (бобика, бобику, бобиком…); латиница
# после имени («бобикXYZ») — не обращение.
_BOBIK_RE = re.compile(r"(?<![\w])@?бобик[а-яё]*(?!\w)", re.IGNORECASE)
_ANSWERED_KEEP = 300  # сколько последних отвеченных сообщений помнить (для правок)


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
            rest = text[len(cs):]
            if rest and (rest[0].isalnum() or rest[0] == "_"):
                continue  # «@бобикXYZ» — не обращение к боту
            return rest.lstrip(" ,:—-\t")
    # Решение владельца 2026-09-19 («пусть флудит»): семья пишет «Бобик привет», «Бобику скажи»,
    # «а бобик знает?» — без запятой и не в начале. Любое «бобик» отдельным словом в любой
    # падежной форме — обращение. В начале фразы имя отрезается, в середине — текст целиком.
    m = _BOBIK_RE.search(text)
    if m:
        if m.start() == 0:
            return text[m.end():].lstrip(" ,:—-!?.\t")
        return text
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
    if low.startswith("забудь"):
        return "forget", None
    if _HEALTH_RE.match(low):
        return "health", None
    return "ask", text.strip()


class TelegramBot:
    def __init__(self, api: TgApi, downloads, answer=None, state_path=None):
        self.api = api
        self.downloads = downloads
        self.beats: dict = {}  # пульс циклов для супервизора
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
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        # Раунд 2 (2026-09-19): раньше личка и группа делили один "strangers" —
        # старый файл состояния считаем личным списком.
        if "strangers" in data and "strangers_private" not in data:
            data["strangers_private"] = data.pop("strangers")
        return data

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

    async def _leave_foreign_group(self, chat_id: int) -> None:
        log.info("telegram foreign group", extra={"fields": {"chat_id": chat_id}})
        seen = self.state.setdefault("foreign_groups_notified", [])
        if chat_id not in seen:
            seen.append(chat_id)
            self._save()
            owner = self._owner_chat()
            if owner:
                await self._say(owner, "🐕 Меня добавили в чужую группу %s — вышел." % chat_id)
        await self.api.call("leaveChat", chat_id=chat_id)

    # ── обработка ─────────────────────────────────────────────────────────────
    async def handle_update(self, upd: dict) -> None:
        mcm = upd.get("my_chat_member")
        if mcm:
            chat = mcm.get("chat") or {}
            if chat.get("type") in ("group", "supergroup") and chat.get("id") != self.family:
                await self._leave_foreign_group(chat["id"])
            return
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat.get("type") in ("group", "supergroup") and chat_id != self.family:
            await self._leave_foreign_group(chat_id)
            return
        text = addressed_text(msg, self.bot_username, self.callsigns)
        if text is None:
            return  # не нам: не обрабатываем, не храним, не пишем в журнал
        # Правка сообщения приходит отдельным событием. Дописали «Бобик» при правке — отвечаем;
        # уже отвеченное сообщение, которое просто подправили, — второй раз не отвечаем.
        key = "%s:%s" % (chat_id, msg.get("message_id"))
        answered = self.state.setdefault("answered", [])
        if key in answered:
            return
        answered.append(key)
        del answered[:-_ANSWERED_KEEP]
        self._save()
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
        # Мелкая правка: ветка документа — раньше проверки пустого текста/справки.
        # Иначе .torrent без подписи в личке (addressed_text даёт "") попадал бы
        # в HELP и не скачивался вовсе.
        if doc and (doc.get("file_name") or "").lower().endswith(".torrent"):
            if kind != "download" and chat.get("type") != "private":
                return
            if int(doc.get("file_size") or 0) > TORRENT_LIMIT:
                await self._say(chat_id, "❌ .torrent-файл больше 20 МБ — пришлите magnet-ссылку.", mid)
                return
            data = await self.api.file_bytes(doc["file_id"])
            await self._say(chat_id, await self.downloads.add_torrent(data, chat_id, login), mid)
            return
        if text == "":
            await self._say(chat_id, GREETING, mid)  # просто «Бобик» — откликнуться, а не молчать
            return
        if text == "/start" or text.startswith("/start@") or text == "/help":
            await self._say(chat_id, HELP)
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
        elif kind == "forget":
            from app import dialog as dialog_mem
            dialog_mem.MEMORY.forget("tg:%s" % chat_id)
            await self._say(chat_id, "🐕 Забыл, начнём сначала.", mid)
        elif kind == "health":
            await self._say(chat_id, await self._health_reply(login), mid)
        else:
            speaker = (msg.get("from") or {}).get("first_name") or login
            await self.api.call("sendChatAction", chat_id=chat_id, action="typing")
            reply = await self.answer(arg, login, dialog=("tg:%s" % chat_id, speaker))
            await self._say(chat_id, reply, mid)

    async def _health_reply(self, login: str) -> str:
        """E3: «что сломалось?» — только владельцу (settings.telegram_owner_login).
        Остальным членам семьи — вежливый отказ, а не подробности о системе."""
        if login != settings.telegram_owner_login:
            return HEALTH_OWNER_ONLY_TEXT
        from app.routers import talk_bot as talk_bot_mod
        return await talk_bot_mod._build_health()

    async def _stranger(self, msg: dict, chat: dict) -> None:
        uid = (msg.get("from") or {}).get("id")
        chat_type = chat.get("type")
        # Метаданные каждой попытки — до дедупликации; дедуп ограничивает только сообщения.
        log.info("telegram stranger", extra={"fields": {"user_id": uid, "chat_type": chat_type}})
        # Личка и группа — разные ключи: один и тот же uid обязан быть замечен в обоих
        # контекстах (раньше общий "strangers" глушил вторую попытку целиком).
        key = "strangers_private" if chat_type == "private" else "strangers_group"
        seen = self.state.setdefault(key, [])
        if uid in seen:
            return
        seen.append(uid)
        self._save()
        name = (msg.get("from") or {}).get("first_name", "")
        if chat_type == "private":
            await self._say(chat["id"], STRANGER_TEXT)
            owner_text = ("🐕 Боту написал незнакомый аккаунт: %s (user_id %s). "
                          "Если это семья — добавьте в TELEGRAM_USERS." % (name, uid))
        else:
            # В общем чате незнакомцу не отвечаем (не шумим), только сообщаем владельцу.
            owner_text = ("🐕 В семейной группе к боту обратился аккаунт не из списка: %s "
                          "(user_id %s). Если это семья — добавьте в TELEGRAM_USERS." % (name, uid))
        owner = self._owner_chat()
        if owner:
            await self._say(owner, owner_text)

    # ── циклы ─────────────────────────────────────────────────────────────────
    async def poll_once(self) -> None:
        offset = self.state.get("offset", 0)
        updates = await self.api.call("getUpdates", offset=offset, timeout=30,
                                      allowed_updates=["message", "edited_message", "my_chat_member"])
        for upd in updates:
            try:
                await self.handle_update(upd)
            except Exception:
                log.exception("telegram update failed")
            self.state["offset"] = upd["update_id"] + 1
            self._save()

    def _beat(self, loop: str) -> None:
        self.beats[loop] = time.monotonic()

    async def poll_forever(self) -> None:
        # 2026-09-26: ловим ЛЮБОЕ исключение, а не только httpx/OSError. SOCKS-прокси
        # при обрыве туннеля отдаёт socksio.ProtocolError — он не наследник httpx.HTTPError,
        # цикл умер молча 20.09 и бот не слышал семью шесть дней при «здоровом» контейнере.
        backoff = 1
        while True:
            try:
                await self.poll_once()
                backoff = 1
                STATUS["last_ok"] = time.time()
                STATUS["state"] = "ok"
            except TgError as exc:
                await asyncio.sleep(exc.retry_after or backoff)
                backoff = min(backoff * 2, 60)
            except Exception as exc:
                STATUS["state"] = "unreachable"
                log.warning("telegram unreachable: %s", type(exc).__name__)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            self._beat("poll")

    async def downloads_once(self) -> None:
        # И1: outbox отправляется по порядку; на первой ошибке останавливаемся —
        # остаток остаётся неподтверждённым и вернётся на следующем такте.
        outbox = await self.downloads.tick()
        sent = 0
        for chat_id, text in outbox:
            try:
                await self._say(chat_id, text)
            except Exception:
                break
            sent += 1
        await self.downloads.ack(sent)

    async def downloads_forever(self, interval: int = 30) -> None:
        while True:
            try:
                await self.downloads_once()
            except Exception:
                log.exception("downloads tick failed")
            self._beat("downloads")
            await asyncio.sleep(interval)


# Состояние для /healthcheck: без токена и без содержимого сообщений.
STATUS = {"state": "starting", "last_ok": 0.0, "restarts": 0}

# Один проход poll_once не дольше таймаута httpx (45 с), пауза — не дольше 60 с;
# пульса нет 5 минут — цикл завис (например, повис на рукопожатии SOCKS), перезапускаем.
STALE_AFTER = 300
CHECK_EVERY = 30
RESTART_DELAY = 5


async def supervise(name: str, factory, beats: dict, stale_after: float = STALE_AFTER,
                    check_every: float = CHECK_EVERY, restart_delay: float = RESTART_DELAY) -> None:
    """Держит цикл живым: упал — перезапуск, завис без пульса — отмена и перезапуск.

    Цикл не должен умирать молча: процесс при этом жив, healthcheck зелёный,
    а бот глух (инцидент 20–26.09). Супервизор сам не падает ни от чего, кроме отмены."""
    while True:
        beats[name] = time.monotonic()
        task = asyncio.ensure_future(factory())
        reason = ""
        while not reason:
            done, _ = await asyncio.wait({task}, timeout=check_every)
            if done:
                exc = None if task.cancelled() else task.exception()
                reason = "упал: %s" % type(exc).__name__ if exc else "завершился"
            elif time.monotonic() - beats.get(name, 0) > stale_after:
                reason = "завис без пульса %d с" % stale_after
                task.cancel()
                try:
                    await task
                except BaseException:  # noqa: B036 — отменённая или упавшая задача, причина уже названа
                    pass
        STATUS["restarts"] += 1
        log.error("telegram: цикл %s %s — перезапуск", name, reason)
        await asyncio.sleep(restart_delay)


async def connect(api: TgApi, bot: "TelegramBot", retry: float = 30) -> None:
    while not bot.bot_username:
        try:
            bot.bot_username = (await api.call("getMe"))["username"]
            STATUS["state"] = "ok"
            STATUS["last_ok"] = time.time()
            log.info("telegram connected", extra={"fields": {"bot": bot.bot_username}})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # И5: виден тип ошибки, но не текст — чтобы не утёк токен из URL исключения httpx.
            STATUS["state"] = "unreachable"
            log.warning("telegram unreachable at start: %s", type(exc).__name__)
            await asyncio.sleep(retry)


async def run() -> None:
    api = TgApi(settings.telegram_bot_token, proxy=settings.telegram_proxy or None)
    bot = TelegramBot(api, downloads_mod.Downloads())
    await connect(api, bot)
    await asyncio.gather(supervise("poll", bot.poll_forever, bot.beats),
                         supervise("downloads", bot.downloads_forever, bot.beats))
