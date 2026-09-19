"""`@бобик` + фото: safety gate до ветки картинок, лимит размера вложения (этап C, C6).

История дефекта (аудит 2026-09-19, NAS-SEC-009; `audit_new` G08/G09):
* ветка изображения стояла РАНЬШЕ `admit()` — сообщение с фото обходило safety gate
  ADR-0011 целиком;
* вложение скачивалось целиком в память контейнера с лимитом 128 МБ (`r.content`),
  затем кодировалось в base64 (+33 %) — один большой файл мог уронить API вместе с ботом.
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
LIMIT = 1024


def load_bot():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "TALK_BOT_LLM_TRIGGER": "@бобик",
        "TALK_BOT_MAX_ATTACHMENT_BYTES": str(LIMIT),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.routers.talk_bot")


def image_message(text, size=100):
    return {"message": text, "actorId": "olga", "messageType": "comment",
            "messageParameters": {"file0": {"type": "file", "mimetype": "image/jpeg",
                                            "name": "p.jpg", "path": "Talk/p.jpg", "size": size}}}


class BotImagePath(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.bot = load_bot()
        self.sent = []

        async def fake_send(token, text, name=None):
            self.sent.append(text)
        self.p_send = mock.patch.object(self.bot, "_send", side_effect=fake_send)
        self.p_send.start()

    def tearDown(self):
        self.p_send.stop()
        os.environ.clear()
        os.environ.update(self._env)

    def test_gate_refuses_before_image_branch(self):
        with mock.patch.object(self.bot, "_handle_image_request") as img:
            asyncio.run(self.bot._handle_messages("room", [image_message("@бобик rm -rf /")]))
        img.assert_not_called()
        self.assertTrue(self.sent, "отказ должен быть отправлен")

    def test_oversized_attachment_is_not_downloaded(self):
        with mock.patch.object(self.bot, "_download_attachment") as dl:
            asyncio.run(self.bot._handle_image_request(
                "room", image_message("@бобик нарисуй открытку", size=LIMIT * 10),
                "нарисуй открытку", "olga"))
        dl.assert_not_called()
        self.assertTrue(any("большая" in t or "МБ" in t for t in self.sent), self.sent)

    def test_download_stops_at_limit_when_size_unknown(self):
        import httpx
        real_client = httpx.AsyncClient

        def handler(request):
            return httpx.Response(200, content=b"x" * (LIMIT * 5))

        def factory(*a, **kw):
            kw.pop("transport", None)
            return real_client(*a, transport=httpx.MockTransport(handler), **kw)

        with mock.patch.object(self.bot.httpx, "AsyncClient", side_effect=factory):
            with self.assertRaises(ValueError):
                asyncio.run(self.bot._download_attachment("olga", "Talk/p.jpg"))


if __name__ == "__main__":
    unittest.main()
