"""Общая функция ответа @бобик — для Talk и Telegram (план качалки, Task 1).

Зачем: Telegram-бот обязан идти тем же путём, что Talk (safety gate ADR-0011 → шлюз с
сервисным токеном → квота по логину). Копия цепочки разошлась бы с оригиналом; поэтому
цепочка вынесена в talk_bot.answer(), а Talk-цикл вызывает её же.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load_bot():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "TALK_BOT_LLM_TRIGGER": "@бобик",
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "TALK_BOT_LLM_DAILY_REPLIES": "2",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.routers.talk_bot")


def test_refused_question_never_reaches_llm(monkeypatch):
    bot = load_bot()
    called = []

    async def fake_llm(q, u, context=""):
        called.append(q)
        return "🐕 ok"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_REFUSE, "tool": None, "message": "🐕 Не могу.", "reason": "t"})
    reply = asyncio.run(bot.answer("удали все файлы", "ivan"))
    assert reply == "🐕 Не могу."
    assert called == []


def test_chat_question_goes_to_llm_and_is_counted(monkeypatch):
    bot = load_bot()

    async def fake_llm(q, u, context=""):
        return "🐕 Париж (%s)" % u

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    before = bot._STATE.get("llm_replied", 0)
    assert asyncio.run(bot.answer("столица Франции?", "olga")) == "🐕 Париж (olga)"
    assert bot._STATE["llm_replied"] == before + 1


def test_llm_exception_becomes_polite_reply(monkeypatch):
    bot = load_bot()

    async def boom(q, u, context=""):
        raise RuntimeError("шлюз упал")

    monkeypatch.setattr(bot, "_ask_llm", boom)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    assert "попробуйте позже" in asyncio.run(bot.answer("вопрос", "admin"))


def test_daily_reply_limit_is_per_user(monkeypatch):
    bot = load_bot()

    async def fake_llm(q, u, context=""):
        return "🐕 ok"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    for _ in range(2):
        assert asyncio.run(bot.answer("q", "ulyana")) == "🐕 ok"
    assert "лимит" in asyncio.run(bot.answer("q", "ulyana"))
    assert asyncio.run(bot.answer("q", "ivan")) == "🐕 ok"


def test_home_tool_answers_locally(monkeypatch):
    bot = load_bot()
    called = []

    async def fake_llm(q, u, context=""):
        called.append(q)
        return "x"

    async def fake_tool(tool, user=""):
        return "🐕 Диск: 7%"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "_dispatch_home_tool", fake_tool)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_EXECUTE, "tool": "disk", "message": None, "reason": "tool_intent"})
    assert asyncio.run(bot.answer("сколько места?", "admin")) == "🐕 Диск: 7%"
    assert called == []


# ── память разговора (спецификация 2026-09-19) ────────────────────────────────

def test_history_is_sent_as_context_and_turns_are_remembered(monkeypatch):
    bot = load_bot()
    seen = {}

    async def fake_llm(q, u, context=""):
        seen["context"] = context
        return "🐕 Паста с курицей."

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    from app import dialog
    dialog.MEMORY.forget("tg:7")
    assert asyncio.run(bot.answer("что приготовить?", "olga", dialog=("tg:7", "Оля"))) == "🐕 Паста с курицей."
    assert seen["context"] == ""          # первый вопрос — истории ещё нет
    asyncio.run(bot.answer("а без мяса?", "ivan", dialog=("tg:7", "Ваня")))
    assert seen["context"] == "Оля: что приготовить? \nБобик: Паста с курицей.".replace(" \n", "\n")
    assert "Ваня: а без мяса?" in dialog.MEMORY.history("tg:7")


def test_answer_without_dialog_keeps_old_behaviour(monkeypatch):
    bot = load_bot()
    seen = {}

    async def fake_llm(q, u, context=""):
        seen["context"] = context
        return "🐕 ок"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    assert asyncio.run(bot.answer("вопрос", "admin")) == "🐕 ок"
    assert seen["context"] == ""


def test_gate_refusal_is_not_remembered(monkeypatch):
    bot = load_bot()
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_REFUSE, "tool": None, "message": "🐕 Не могу.", "reason": "deny"})
    from app import dialog
    dialog.MEMORY.forget("tg:8")
    asyncio.run(bot.answer("удали всё", "ivan", dialog=("tg:8", "Ваня")))
    assert dialog.MEMORY.history("tg:8") == ""


def test_gateway_failure_is_not_remembered(monkeypatch):
    bot = load_bot()

    async def boom(q, u, context=""):
        raise RuntimeError("шлюз упал")

    monkeypatch.setattr(bot, "_ask_llm", boom)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    from app import dialog
    dialog.MEMORY.forget("tg:9")
    reply = asyncio.run(bot.answer("вопрос", "ivan", dialog=("tg:9", "Ваня")))
    assert "попробуйте позже" in reply
    assert dialog.MEMORY.history("tg:9") == ""


def test_context_is_passed_to_gateway_payload(monkeypatch):
    """Историю должен получить именно шлюз — проверяем тело запроса, а не обёртку."""
    bot = load_bot()
    sent = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"content": "ответ"}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            sent.update(json or {})
            return FakeResponse()

    monkeypatch.setattr(bot.httpx, "AsyncClient", FakeClient)
    asyncio.run(bot._ask_llm("вопрос", "ivan", context="Оля: раз\nБобик: два"))
    assert sent["context"] == "Оля: раз\nБобик: два"
    assert sent["prompt"] == "вопрос"
