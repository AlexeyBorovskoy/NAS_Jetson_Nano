"""Контрактные тесты LLM Gateway на уровне HTTP (без сети, без секретов).

История дефектов (аудит 2026-09-19, NAS-REG-001, разбор работы GigaCode):
* `d52c11b` — `chat()` обращался к `full` до присваивания: КАЖДЫЙ чат GigaChat → 500.
  Новые тесты проверяли вспомогательную функцию, а не эндпоинт, и дефект прошёл.
* там же удалён `_IMG_TAG_RE`, который всё ещё используется → генерация картинок падает.
* W0.2 перевёл эндпоинты в `async def` при блокирующих вызовах внутри → event loop
  стоял на время запроса к LLM, `/health` отвечал через 6 с вместо 0.5 с.
* импорт модуля создавал `/data/images` (на Windows — `E:\\data` в корне диска).

Поэтому здесь проверяется поведение эндпоинтов, а не функции по отдельности.
Run: python -m pytest tests/llm_gateway -q
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "services" / "llm-gateway"
sys.path.insert(0, str(GW))


class GatewayCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.tmp = tempfile.mkdtemp()
        for k in [k for k in os.environ if k.startswith(("LLM_", "GIGACHAT_", "DEEPSEEK_", "CLOUDRU_"))]:
            del os.environ[k]
        os.environ.update({
            "LLM_USAGE_FILE": os.path.join(self.tmp, "usage.json"),
            "IMAGE_OUTPUT_ROOT": os.path.join(self.tmp, "images"),
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_AUTH_KEY": "test-key",
            "DEEPSEEK_API_KEY": "test-ds",
            "LLM_GATEWAY_SERVICE_TOKEN": "",
        })

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]

    def load(self, **env):
        os.environ.update(env)
        # Оба сервиса называют пакет `app` — свой сервис обязан стоять первым.
        if str(GW) in sys.path:
            sys.path.remove(str(GW))
        sys.path.insert(0, str(GW))
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]
        return importlib.import_module("app.main")

    def client(self, m):
        from fastapi.testclient import TestClient
        return TestClient(m.app, raise_server_exceptions=False)


class ChatEndpoint(GatewayCase):
    def test_gigachat_chat_returns_200(self):
        m = self.load()
        with mock.patch.object(m, "_call_gigachat", return_value=("ответ", 7)):
            r = self.client(m).post("/v1/chat", json={"prompt": "Как дела?", "user": "t"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["provider"], "gigachat")

    def test_technical_russian_prompt_returns_200(self):
        m = self.load()
        with mock.patch.object(m, "_call_gigachat", return_value=("ок", 3)):
            r = self.client(m).post("/v1/chat", json={"prompt": "docker выдаёт ошибку", "user": "t"})
        self.assertEqual(r.status_code, 200, r.text)


class ImageEndpoint(GatewayCase):
    def test_generate_extracts_file_id_from_img_tag(self):
        m = self.load()
        answer = mock.Mock(status_code=200)
        answer.json.return_value = {
            "choices": [{"message": {"content": 'Готово <img src="file-123" fuse="true"/>'}}],
            "usage": {"total_tokens": 5},
        }
        with mock.patch.object(m, "_gigachat_access_token", return_value="tok"), \
                mock.patch.object(m.httpx, "post", return_value=answer), \
                mock.patch.object(m, "_gigachat_download_file", return_value=b"\xff\xd8jpeg") as dl:
            r = self.client(m).post("/v1/image/generate", json={"prompt": "кот", "user": "t"})
        self.assertEqual(r.status_code, 200, r.text)
        dl.assert_called_once_with("file-123")


class NoSideEffectsOnImport(GatewayCase):
    def test_import_does_not_create_image_dir(self):
        target = os.path.join(self.tmp, "not-yet")
        self.load(IMAGE_OUTPUT_ROOT=target)
        self.assertFalse(os.path.exists(target), "каталог создан при импорте модуля")


class EventLoopNotBlocked(GatewayCase):
    def test_health_answers_while_llm_call_is_slow(self):
        import httpx
        m = self.load()

        def slow(*_a, **_k):
            time.sleep(2)
            return ("ok", 1)

        async def scenario():
            transport = httpx.ASGITransport(app=m.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://gw") as c:
                # Время — от старта сценария: при заблокированном loop даже sleep(0.3)
                # «просыпается» только после конца чата, и замер после него ничего не видит.
                t0 = time.monotonic()
                chat = asyncio.ensure_future(
                    c.post("/v1/chat", json={"prompt": "hi", "provider": "deepseek"}, timeout=30))
                await asyncio.sleep(0.3)
                h = await c.get("/health")
                took = time.monotonic() - t0
                await chat
                return h.status_code, took

        with mock.patch.object(m, "_call_deepseek", side_effect=slow):
            status, took = asyncio.run(scenario())
        self.assertEqual(status, 200)
        self.assertLess(took, 1.2, "/health ждал окончания запроса к LLM: %.1f с" % took)


if __name__ == "__main__":
    unittest.main()
