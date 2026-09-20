"""Talk-цикл @бобик: память разговора по комнатам (финальное ревью, F1).

История дефекта: до этого теста Talk-половина памяти разговора не была покрыта
вовсе — ревьюер 2026-09-20 доказал мутациями, что все 116 тестов проходят, если
(1) убрать чтение/запись памяти из `_handle_messages`, ИЛИ (2) заменить ключ
`"talk:%s" % token` константой. Вторая мутация означала бы слияние шести личных
комнат Talk в одну общую нить — то есть ответ Ване мог бы содержать контекст
вопроса Оли. Этот файл ловит обе мутации.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load_bot():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "TALK_BOT_LLM_TRIGGER": "@бобик",
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.routers.talk_bot")


def text_message(text, actor_id, display_name):
    """Текстовое сообщение Talk (без вложения — ветка картинок сюда не заходит)."""
    return {
        "message": text,
        "actorId": actor_id,
        "actorDisplayName": display_name,
        "messageType": "comment",
    }


class TalkDialogMemory(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.bot = load_bot()
        self.sent = []
        self.asked_context = []

        async def fake_send(token, text, name=None):
            self.sent.append((token, text))
        self.p_send = mock.patch.object(self.bot, "_send", side_effect=fake_send)
        self.p_send.start()

        async def fake_ask_llm(question, user, context=""):
            self.asked_context.append(context)
            return "🐕 ответ на: %s" % question
        self.p_ask = mock.patch.object(self.bot, "_ask_llm", side_effect=fake_ask_llm)
        self.p_ask.start()

        def fake_admit(text, structured_tools=True):
            return {
                "decision": self.bot.ADMIT_CHAT,
                "tool": None,
                "message": None,
                "reason": "chat",
            }
        self.p_admit = mock.patch.object(self.bot, "admit", side_effect=fake_admit)
        self.p_admit.start()

    def tearDown(self):
        self.p_admit.stop()
        self.p_ask.stop()
        self.p_send.stop()
        os.environ.clear()
        os.environ.update(self._env)

    def test_rooms_get_separate_memory_keys_and_history_is_isolated(self):
        from app import dialog
        asyncio.run(self.bot._handle_messages(
            "room1", [text_message("@бобик что приготовить?", "olga", "Оля")]))
        asyncio.run(self.bot._handle_messages(
            "room2", [text_message("@бобик какая погода?", "ivan", "Ваня")]))

        hist1 = dialog.MEMORY.history("talk:room1")
        hist2 = dialog.MEMORY.history("talk:room2")
        self.assertIn("Оля: что приготовить?", hist1)
        self.assertIn("Ваня: какая погода?", hist2)
        # ключи не должны схлопнуться в один — своя комната не видит чужую историю
        self.assertNotIn("Оля", hist2)
        self.assertNotIn("Ваня", hist1)

    def test_second_question_in_same_room_carries_prior_context(self):
        asyncio.run(self.bot._handle_messages(
            "room1", [text_message("@бобик что приготовить?", "olga", "Оля")]))
        self.assertEqual(self.asked_context[0], "")  # первый вопрос — истории ещё нет

        asyncio.run(self.bot._handle_messages(
            "room1", [text_message("@бобик а без мяса?", "olga", "Оля")]))
        self.assertEqual(len(self.asked_context), 2)
        self.assertIn("Оля: что приготовить?", self.asked_context[1])
        self.assertIn("Бобик:", self.asked_context[1])

    def test_speaker_is_taken_from_actor_display_name(self):
        from app import dialog
        asyncio.run(self.bot._handle_messages(
            "room1", [text_message("@бобик привет", "olga", "Оленька")]))
        # actorId="olga" не должен попасть в историю как имя говорящего
        self.assertIn("Оленька: привет", dialog.MEMORY.history("talk:room1"))
        self.assertNotIn("olga:", dialog.MEMORY.history("talk:room1"))


if __name__ == "__main__":
    unittest.main()
