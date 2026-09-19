"""Telegram-фронт @бобик: обращение, белый список, маршрутизация, опрос (спецификация §4, §7).
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"
FAMILY = -100123
OWNER, SON, STRANGER = 111, 222, 999


def load():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "TELEGRAM_USERS": "%d:admin %d:ivan" % (OWNER, SON),
        "TELEGRAM_FAMILY_CHAT_ID": str(FAMILY),
        "TELEGRAM_OWNER_LOGIN": "admin",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.telegram_bot")


class FakeTelegram:
    """httpx.MockTransport: отвечает как Bot API, записывает запросы."""

    def __init__(self, updates=None, file_bytes=b"d8:announce1:xe"):
        self.sent = []
        self.updates = updates or []
        self.file_bytes = file_bytes

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/file/bot" in path:
            return httpx.Response(200, content=self.file_bytes)
        method = path.rsplit("/", 1)[-1]
        body = json.loads(request.content or b"{}")
        self.sent.append((method, body))
        if method == "getMe":
            return httpx.Response(200, json={"ok": True, "result": {"id": 1, "username": "bobik_borovskoy_bot"}})
        if method == "getUpdates":
            ups, self.updates = self.updates, []
            return httpx.Response(200, json={"ok": True, "result": ups})
        if method == "getFile":
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "docs/x.torrent", "file_size": 20}})
        return httpx.Response(200, json={"ok": True, "result": True})

    def texts(self):
        return [(b.get("chat_id"), b.get("text")) for m, b in self.sent if m == "sendMessage"]


class FakeDownloads:
    def __init__(self):
        self.calls = []
        self.acks = []

    async def add_link(self, link, chat_id, user):
        self.calls.append(("link", link, chat_id, user))
        return "⏬ Принял: x"

    async def add_torrent(self, data, chat_id, user):
        self.calls.append(("torrent", data, chat_id, user))
        return "⏬ Принял торрент, проверяю размер…"

    async def list_text(self):
        return "Закачек нет."

    async def cancel(self, n):
        self.calls.append(("cancel", n))
        return "🗑 Отменил: x"

    async def tick(self):
        return [(FAMILY, "✅ Готово: x")]

    async def ack(self, n):
        self.acks.append(n)


def make(tg=None):
    mod = load()
    tg = tg or FakeTelegram()
    api = mod.TgApi("TOKEN", base="https://tg.test", transport=httpx.MockTransport(tg.handler))
    asked = []

    async def answer(q, user):
        asked.append((q, user))
        return "🐕 ответ"

    dl = FakeDownloads()
    bot = mod.TelegramBot(api, dl, answer=answer,
                          state_path=os.path.join(tempfile.mkdtemp(), "tg.json"))
    bot.bot_username = "bobik_borovskoy_bot"
    return mod, bot, tg, dl, asked


_MID = [0]


def msg(text, chat=FAMILY, chat_type="supergroup", uid=SON, **extra):
    # у каждого сообщения свой message_id, как в Telegram (бот помнит отвеченные — для правок)
    _MID[0] += 1
    m = {"message_id": _MID[0], "chat": {"id": chat, "type": chat_type},
         "from": {"id": uid, "first_name": "Ваня"}, "text": text}
    m.update(extra)
    return {"update_id": 10, "message": m}


# ── обращение ─────────────────────────────────────────────────────────────────

def test_addressed_text_variants():
    mod = load()
    cs = ["@бобик", "бобик,"]
    g = {"chat": {"type": "supergroup"}}
    assert mod.addressed_text(dict(g, text="@Бобик скачай x"), "bobik_borovskoy_bot", cs) == "скачай x"
    assert mod.addressed_text(dict(g, text="бобик, закачки"), "bobik_borovskoy_bot", cs) == "закачки"
    assert mod.addressed_text(dict(g, text="@bobik_borovskoy_bot привет"), "bobik_borovskoy_bot", cs) == "привет"
    assert mod.addressed_text(dict(g, text="ответ", reply_to_message={"from": {"username": "bobik_borovskoy_bot"}}),
                              "bobik_borovskoy_bot", cs) == "ответ"
    # решение владельца 2026-09-19 («пусть флудит»): «бобик» в любом месте и форме — обращение
    assert mod.addressed_text(dict(g, text="бобик молодец"), "bobik_borovskoy_bot", cs) == "молодец"
    assert mod.addressed_text({"chat": {"type": "private"}, "text": "привет"}, "bobik_borovskoy_bot", cs) == "привет"


def test_addressed_text_requires_word_boundary():
    mod = load()
    cs = ["@бобик", "бобик,"]
    g = {"chat": {"type": "supergroup"}}
    assert mod.addressed_text(dict(g, text="@бобикXYZ привет"), "bobik_borovskoy_bot", cs) is None
    assert mod.addressed_text(dict(g, text="@bobik_borovskoy_bot_fake hi"), "bobik_borovskoy_bot", cs) is None
    assert mod.addressed_text(dict(g, text="@бобик, привет"), "bobik_borovskoy_bot", cs) == "привет"
    assert mod.addressed_text(dict(g, text="@бобик"), "bobik_borovskoy_bot", cs) == ""


def test_route():
    mod = load()
    assert mod.route("скачай magnet:?xt=urn:btih:A") == ("download", "magnet:?xt=urn:btih:A")
    assert mod.route("Закачки") == ("list", None)
    assert mod.route("отмени 2") == ("cancel", 2)
    assert mod.route("какая погода?") == ("ask", "какая погода?")


def test_parse_users():
    mod = load()
    assert mod.parse_users("1:admin 2:ivan bad 3:") == {1: "admin", 2: "ivan"}


# ── поведение ─────────────────────────────────────────────────────────────────

def test_unaddressed_group_message_is_ignored_silently():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("мам, купи хлеба")))
    assert tg.texts() == [] and asked == [] and dl.calls == []


def test_download_command_from_son_in_group():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:ABC")))
    assert dl.calls == [("link", "magnet:?xt=urn:btih:ABC", FAMILY, "ivan")]
    assert tg.texts() == [(FAMILY, "⏬ Принял: x")]


def test_bad_link_explained():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик скачай http://192.168.0.50/x")))
    assert dl.calls == []
    assert tg.texts()[0][1].startswith("❌")


def test_question_goes_to_gigachat_path_with_login():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("бобик, столица Франции?")))
    assert asked == [("столица Франции?", "ivan")]
    assert ("sendChatAction", {"chat_id": FAMILY, "action": "typing"}) in tg.sent
    assert tg.texts() == [(FAMILY, "🐕 ответ")]


def test_lookalike_callsign_is_not_addressed():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобикXYZ вопрос")))
    assert asked == [] and dl.calls == [] and tg.texts() == []


def test_list_and_cancel():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик закачки")))
    asyncio.run(bot.handle_update(msg("@бобик отмени 3")))
    assert ("cancel", 3) in dl.calls
    assert [t for _, t in tg.texts()] == ["Закачек нет.", "🗑 Отменил: x"]


def test_torrent_document_with_caption():
    mod, bot, tg, dl, asked = make()
    upd = msg(None, caption="@бобик скачай",
              document={"file_id": "F1", "file_name": "distro.torrent", "file_size": 20})
    upd["message"].pop("text")
    asyncio.run(bot.handle_update(upd))
    assert dl.calls and dl.calls[0][0] == "torrent" and dl.calls[0][1] == b"d8:announce1:xe"


def test_torrent_in_private_without_caption_still_downloads():
    # Мелкая правка: ветка документа обязана идти раньше проверки пустого текста —
    # иначе .torrent без подписи в личке уходил в «справку» вместо закачки.
    mod, bot, tg, dl, asked = make()
    upd = msg(None, chat=OWNER, chat_type="private", uid=OWNER,
              document={"file_id": "F1", "file_name": "distro.torrent", "file_size": 20})
    upd["message"].pop("text")
    asyncio.run(bot.handle_update(upd))
    assert dl.calls and dl.calls[0][0] == "torrent"
    assert tg.texts() == [(OWNER, "⏬ Принял торрент, проверяю размер…")]


def test_torrent_over_20mb_refused():
    mod, bot, tg, dl, asked = make()
    upd = msg(None, caption="@бобик скачай",
              document={"file_id": "F1", "file_name": "big.torrent", "file_size": 21 * 1024 * 1024})
    upd["message"].pop("text")
    asyncio.run(bot.handle_update(upd))
    assert dl.calls == []
    assert "20 МБ" in tg.texts()[0][1]


def test_stranger_in_private_gets_one_reply_and_owner_is_told():
    mod, bot, tg, dl, asked = make()
    for _ in range(2):
        asyncio.run(bot.handle_update(msg("/start", chat=STRANGER, chat_type="private", uid=STRANGER)))
    texts = tg.texts()
    assert sum(1 for c, _ in texts if c == STRANGER) == 1
    assert any(c == OWNER and str(STRANGER) in t for c, t in texts)
    assert asked == []


def test_stranger_in_family_group_stays_silent_and_owner_is_told_once():
    mod, bot, tg, dl, asked = make()
    for _ in range(2):
        asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:A", uid=STRANGER)))
    texts = tg.texts()
    assert [t for c, t in texts if c == FAMILY] == []
    assert dl.calls == []
    assert asked == []
    owner_texts = [t for c, t in texts if c == OWNER]
    assert len(owner_texts) == 1
    assert str(STRANGER) in owner_texts[0]


def test_stranger_group_then_private_both_reported():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик привет", uid=STRANGER)))
    asyncio.run(bot.handle_update(msg("/start", chat=STRANGER, chat_type="private", uid=STRANGER)))
    texts = tg.texts()
    assert [t for c, t in texts if c == STRANGER] == [mod.STRANGER_TEXT]
    assert len([t for c, t in texts if c == OWNER]) == 2
    assert asked == []


def test_stranger_private_then_group_both_reported():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("/start", chat=STRANGER, chat_type="private", uid=STRANGER)))
    asyncio.run(bot.handle_update(msg("@бобик привет", uid=STRANGER)))
    texts = tg.texts()
    assert [t for c, t in texts if c == STRANGER] == [mod.STRANGER_TEXT]
    assert len([t for c, t in texts if c == OWNER]) == 2
    assert asked == []


def test_foreign_group_is_left():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик привет", chat=-555)))
    assert ("leaveChat", {"chat_id": -555}) in tg.sent
    assert asked == []


def test_foreign_group_owner_notified_once():
    # Мелкая правка: владелец узнаёт о чужой группе, но не при каждом сообщении из неё.
    mod, bot, tg, dl, asked = make()
    for _ in range(2):
        asyncio.run(bot.handle_update(msg("@бобик привет", chat=-555)))
    leave_calls = [b for m, b in tg.sent if m == "leaveChat"]
    assert leave_calls == [{"chat_id": -555}, {"chat_id": -555}]
    owner_texts = [t for c, t in tg.texts() if c == OWNER]
    assert len(owner_texts) == 1
    assert "-555" in owner_texts[0]


def test_poll_saves_offset_after_processing(tmp_path):
    tg = FakeTelegram(updates=[dict(msg("@бобик закачки"), update_id=41)])
    mod, bot, tg, dl, asked = make(tg)
    asyncio.run(bot.poll_once())
    assert json.load(open(bot.state_path, encoding="utf-8"))["offset"] == 42


def test_retry_after_is_respected():
    mod = load()

    def handler(request):
        return httpx.Response(429, json={"ok": False, "error_code": 429,
                                         "parameters": {"retry_after": 7}})

    api = mod.TgApi("TOKEN", base="https://tg.test", transport=httpx.MockTransport(handler))
    try:
        asyncio.run(api.call("sendMessage", chat_id=1, text="x"))
    except mod.TgError as exc:
        assert exc.retry_after == 7
    else:
        raise AssertionError("ожидался TgError")


def test_download_notifications_are_sent():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.downloads_once())
    assert tg.texts() == [(FAMILY, "✅ Готово: x")]
    assert dl.acks == [1]          # И1: подтверждено ровно столько, сколько отправлено


def test_download_notification_failure_keeps_outbox_unacked():
    # И1: sendMessage падает (500) — ack(0), остальное остаётся в outbox бота-учёта.
    def handler(request):
        path = request.url.path
        method = path.rsplit("/", 1)[-1]
        if method == "sendMessage":
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True, "result": True})

    mod = load()
    api = mod.TgApi("TOKEN", base="https://tg.test", transport=httpx.MockTransport(handler))
    dl = FakeDownloads()

    async def answer(q, user):
        return "🐕 ответ"

    bot = mod.TelegramBot(api, dl, answer=answer, state_path=os.path.join(tempfile.mkdtemp(), "tg.json"))
    asyncio.run(bot.downloads_once())
    assert dl.acks == [0]


def test_token_never_logged(caplog):
    mod, bot, tg, dl, asked = make()
    with caplog.at_level("DEBUG"):
        asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:ABC")))
    assert "TOKEN" not in caplog.text
    assert "magnet:?xt" not in caplog.text


# ── «пусть флудит» (решение владельца 2026-09-19, по скриншоту группы) ─────────

def test_bobik_anywhere_any_form_is_addressed():
    mod = load()
    cs = ["@бобик", "бобик,"]
    g = {"chat": {"type": "supergroup"}}
    at = lambda t: mod.addressed_text(dict(g, text=t), "bobik_borovskoy_bot", cs)
    assert at("Бобик привет") == "привет"
    assert at("Бобик! я хочу есть, но меня не кормят") == "я хочу есть, но меня не кормят"
    assert at("Бобику скажи спасибо") == "скажи спасибо"
    assert at("а бобик знает, сколько времени?") == "а бобик знает, сколько времени?"
    assert at("Бобик") == ""
    assert at("бобикXYZ привет") is None
    assert at("мам, купи хлеба") is None


def test_bare_bobik_gets_short_greeting():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("Бобик")))
    texts = tg.texts()
    assert len(texts) == 1 and "Гав" in texts[0][1]
    assert asked == []


def test_edited_message_with_bobik_is_answered_once():
    mod, bot, tg, dl, asked = make()
    first = msg("я хочу есть")
    first["message"]["message_id"] = 77
    asyncio.run(bot.handle_update(first))          # без обращения — тишина
    edited = {"update_id": 11, "edited_message": dict(first["message"], text="Бобик, я хочу есть")}
    asyncio.run(bot.handle_update(edited))
    asyncio.run(bot.handle_update(dict(edited, update_id=12)))   # правка ещё раз — не отвечаем повторно
    assert asked == [("я хочу есть", "ivan")]


def test_answered_message_edited_is_not_answered_again():
    mod, bot, tg, dl, asked = make()
    m = msg("Бобик, привет")
    m["message"]["message_id"] = 78
    asyncio.run(bot.handle_update(m))
    asyncio.run(bot.handle_update({"update_id": 13, "edited_message": dict(m["message"], text="Бобик, привет!")}))
    assert asked == [("привет", "ivan")]


def test_poll_asks_for_edited_messages():
    tg = FakeTelegram()
    mod, bot, tg, dl, asked = make(tg)
    asyncio.run(bot.poll_once())
    params = [b for m, b in tg.sent if m == "getUpdates"][0]
    assert "edited_message" in params["allowed_updates"]
