"""Голосовой путь @бобик (E10): приватность, отказы, очередь распознавания.

Спецификация: docs/superpowers/specs/2026-09-20-voice-messages-design.md (§5, §6, §8, §9).
Run: python -m pytest tests/nas_api -q

Фейки TgApi/Downloads и фабрика текстовых сообщений переиспользуются из test_telegram_bot
(свой обработчик бота второй раз не пишем — иначе тесты разойдутся с живым кодом).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import httpx
import pytest

from test_telegram_bot import (FAMILY, OWNER, SON, STRANGER, FakeTelegram,  # noqa: F401
                               load, make)

# Ни одна проверка приватности не должна проходить на пустом совпадении: текст, который
# обязан нигде не сохраниться, специально не похож ни на ключи state, ни на служебные строки.
SECRET = "тайное слово бульбулятор"

_VMID = [900000]


# ── вспомогательное ───────────────────────────────────────────────────────────

def voice_msg(*, chat=FAMILY, chat_type="supergroup", uid=SON, duration=5,
              file_id="VOICE1", file_size=1000, **extra) -> dict:
    """Апдейт с голосовым — так его отдаёт Telegram (message.voice, без text)."""
    _VMID[0] += 1
    m = {"message_id": _VMID[0], "chat": {"id": chat, "type": chat_type},
         "from": {"id": uid, "first_name": "Ваня"},
         "voice": {"file_id": file_id, "duration": duration, "file_size": file_size}}
    m.update(extra)
    return {"update_id": _VMID[0], "message": m}


def run_bot(coro, timeout: float = 2.0):
    """Гоняет корутину с потолком по времени: зависший бот обязан упасть тестом (§8)."""
    async def guarded():
        return await asyncio.wait_for(coro, timeout)
    return asyncio.run(guarded())


def stt_spy(monkeypatch, mod, text="бобик, привет", exc=None) -> list:
    """Подменяет распознавание (bot зовёт app.stt.transcribe) и записывает поданные байты."""
    calls = []

    async def fake(data):
        calls.append(data)
        if exc is not None:
            raise exc
        return text

    monkeypatch.setattr(mod.stt_mod, "transcribe", fake)
    return calls


def file_spy(monkeypatch, bot, content=b"OGG") -> list:
    """Следит, скачивался ли файл голосового вообще (спецификация §8: «файл не скачивается»)."""
    calls = []

    async def fake(file_id, limit=None):
        calls.append(file_id)
        return content

    monkeypatch.setattr(bot.api, "file_bytes", fake)
    return calls


def records_dump(caplog) -> str:
    """Журнал целиком, вместе с extra-полями: текст мог бы уехать и в них, не в сообщение."""
    return "\n".join("%s|%s|%r" % (r.name, r.getMessage(), r.__dict__) for r in caplog.records)


def voice_counters(bot) -> dict:
    return {k: v for k, v in bot.state.items() if k.startswith("voice_")}


def state_raw(bot) -> str:
    """Файл состояния целиком — проверяется отсутствие подстроки, а не только ключей."""
    return Path(bot.state_path).read_text(encoding="utf-8")


class FakeClock:
    """Подмена модуля time внутри telegram_bot: интервал уведомлений — без ожидания."""

    def __init__(self, now: float):
        self.now = now

    def time(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return time.monotonic()


# ── §5/§9.1 приватность: в группе без «бобика» — молчание и нигде ни строчки ────

def test_group_voice_without_callsign_is_silent_and_stores_nothing(monkeypatch, caplog):
    mod, bot, tg, dl, asked = make()
    stt = stt_spy(monkeypatch, mod, text=SECRET)
    file_spy(monkeypatch, bot)
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)

    with caplog.at_level(logging.DEBUG):
        run_bot(bot.handle_update(voice_msg(uid=SON, duration=6)))

    assert stt == [b"OGG"], "распознавание обязано было состояться, иначе проверка пустая"
    assert "voice ignored" in caplog.text, "журнал обязан ловиться — иначе проверка ниже пустая"
    assert tg.texts() == [], "в группе на голосовое без «бобика» бот молчит"
    assert [m for m, _ in tg.sent] == [], "наружу не уходит ничего, включая sendChatAction"
    assert asked == [], "вопрос без «бобика» не уходит в модель"
    assert dialog.MEMORY.history(key) == "", "память диалога не тронута"
    assert voice_counters(bot) == {"voice_ignored": 1}, "остаётся только счётчик без содержимого"
    assert SECRET not in state_raw(bot)
    assert SECRET not in json.dumps(bot.state, ensure_ascii=False)
    assert SECRET not in caplog.text
    assert SECRET not in records_dump(caplog)


def test_group_voice_without_callsign_on_second_message_still_stores_nothing(monkeypatch):
    # Счётчик растёт, а содержимое не копится: во втором прогоне проверяем, что накопление
    # не появилось где-то ещё (например, в «answered» или в записи диалога).
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text=SECRET)
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)

    for _ in range(2):
        run_bot(bot.handle_update(voice_msg(uid=SON, duration=6)))

    assert voice_counters(bot) == {"voice_ignored": 2}
    assert dialog.MEMORY.history(key) == ""
    assert SECRET not in state_raw(bot)
    assert tg.texts() == [] and asked == []
    assert "answered" not in bot.state, "игнорируемое голосовое не помечается как отвеченное"


# ── §6/§9.2 голосовое длиннее 60 с: отказ, файл не скачивается ─────────────────

def test_voice_too_long_in_private_is_refused_without_download(monkeypatch):
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(chat=OWNER, chat_type="private", uid=OWNER, duration=61)))

    assert tg.texts() == [(OWNER, mod.VOICE_TOO_LONG_TEXT)]
    assert files == [], "длинное голосовое не скачивается вовсе"
    assert stt == [], "и не распознаётся"
    assert voice_counters(bot) == {"voice_too_long": 1}
    assert asked == []


def test_voice_too_long_in_group_is_silent_without_download(monkeypatch):
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=61)))

    assert tg.texts() == [], "в группе отказ не спамим"
    assert files == [] and stt == []
    assert voice_counters(bot) == {"voice_too_long": 1}


def test_voice_exactly_60_seconds_is_still_recognized(monkeypatch):
    # Граница: предел — «больше 60», а не «60 и больше» (спецификация §6).
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod, text="бобик, привет")

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=60)))

    assert files == ["VOICE1"] and stt == [b"OGG"]
    assert voice_counters(bot) == {"voice_ok": 1}
    assert asked == [("привет", "ivan", ("tg:%d" % FAMILY, "Ваня"))]


def test_voice_over_size_limit_is_refused_like_too_long(monkeypatch):
    # Длительность в норме, но файл больше voice_max_bytes: в Telegram это независимые
    # величины, и 60 с опус может весить больше 2 МБ.
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(
        chat=OWNER, chat_type="private", uid=OWNER, duration=10,
        file_size=mod.settings.voice_max_bytes + 1)))

    assert tg.texts() == [(OWNER, mod.VOICE_TOO_LONG_TEXT)]
    assert files == [] and stt == []
    assert voice_counters(bot) == {"voice_too_long": 1}


# ── §6/§8/§9.3 «скачай» голосом не выполняется ────────────────────────────────

def test_voice_download_command_is_not_executed(monkeypatch):
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text="бобик, скачай magnet:?xt=urn:btih:AAA")
    parse_calls = []

    def parse_spy(text):
        parse_calls.append(text)
        raise AssertionError("ссылку из голоса разбирать нельзя — закачка не того")

    monkeypatch.setattr(mod.downloads_mod, "parse_link", parse_spy)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=8)))

    assert dl.calls == [], "add_link/add_torrent не вызываются"
    assert parse_calls == []
    texts = tg.texts()
    assert len(texts) == 1 and texts[0][0] == FAMILY
    assert "Расслышал" in texts[0][1], "человек видит, что именно услышал бот"
    assert "magnet:?xt=urn:btih:AAA" in texts[0][1]
    assert "текстом" in texts[0][1], "и получает просьбу прислать ссылку текстом"
    assert voice_counters(bot) == {"voice_ok": 1}
