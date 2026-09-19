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

    async def fake_llm(q, u):
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

    async def fake_llm(q, u):
        return "🐕 Париж (%s)" % u

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    before = bot._STATE.get("llm_replied", 0)
    assert asyncio.run(bot.answer("столица Франции?", "olga")) == "🐕 Париж (olga)"
    assert bot._STATE["llm_replied"] == before + 1


def test_llm_exception_becomes_polite_reply(monkeypatch):
    bot = load_bot()

    async def boom(q, u):
        raise RuntimeError("шлюз упал")

    monkeypatch.setattr(bot, "_ask_llm", boom)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    assert "попробуйте позже" in asyncio.run(bot.answer("вопрос", "admin"))


def test_daily_reply_limit_is_per_user(monkeypatch):
    bot = load_bot()

    async def fake_llm(q, u):
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

    async def fake_llm(q, u):
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
