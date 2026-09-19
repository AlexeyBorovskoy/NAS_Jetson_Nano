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


def msg(text, chat=FAMILY, chat_type="supergroup", uid=SON, **extra):
    m = {"message_id": 5, "chat": {"id": chat, "type": chat_type},
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
    assert mod.addressed_text(dict(g, text="бобик молодец"), "bobik_borovskoy_bot", cs) is None
    assert mod.addressed_text({"chat": {"type": "private"}, "text": "привет"}, "bobik_borovskoy_bot", cs) == "привет"


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


def test_foreign_group_is_left():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик привет", chat=-555)))
    assert ("leaveChat", {"chat_id": -555}) in tg.sent
    assert asked == []


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


def test_token_never_logged(caplog):
    mod, bot, tg, dl, asked = make()
    with caplog.at_level("DEBUG"):
        asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:ABC")))
    assert "TOKEN" not in caplog.text
    assert "magnet:?xt" not in caplog.text
