"""CQ-04 (code audit 2026-10-02): почему шлюз ушёл с локальной модели в облако.

`_local_available()` ловил любое исключение и тихо возвращал False — причина (станция
выключена? туннель лёг? не тот порт?) терялась совсем, а она же решает, кто платит за
следующий вопрос: DeepSeek/GigaChat вместо бесплатной локальной qwen3.5 на станции.
`_LOCAL_LAST_ERROR` хранит короткую причину последней неудачи, видна в `/health`
(`ollama_last_error`), сбрасывается в None при первом же успешном ответе и не спамит
журнал повторной одной и той же причиной.

Run: python -m pytest tests/llm_gateway -q
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "services" / "llm-gateway"
sys.path.insert(0, str(GW))


class LocalModelHealthCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        for k in [k for k in os.environ if k.startswith(("LLM_", "GIGACHAT_", "DEEPSEEK_", "CLOUDRU_"))]:
            del os.environ[k]

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]

    def load(self, **env):
        import tempfile
        tmp = tempfile.mkdtemp()
        os.environ.update({
            "LLM_USAGE_FILE": os.path.join(tmp, "usage.json"),
            "IMAGE_OUTPUT_ROOT": os.path.join(tmp, "images"),
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_AUTH_KEY": "test-key",
            "DEEPSEEK_API_KEY": "test-ds",
            "LLM_GATEWAY_SERVICE_TOKEN": "",
            "LLM_LOCAL_URL": "http://workstation:11434",
        })
        os.environ.update(env)
        if str(GW) in sys.path:
            sys.path.remove(str(GW))
        sys.path.insert(0, str(GW))
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]
        return importlib.import_module("app.main")


class HealthReportsLastError(LocalModelHealthCase):
    # `/health` сам вызывает `_local_available()` (поле "ollama"), поэтому мок обязан
    # оставаться активным ДО чтения `/health`, а не только вокруг отдельного вызова
    # `_local_available()` — иначе health() сходил бы за правдой в реальную сеть.

    def test_exception_is_visible_in_health(self):
        m = self.load()
        with mock.patch.object(m.httpx, "get", side_effect=ConnectionError("туннель лёг")):
            h = m.health()
        self.assertIn("ollama_last_error", h)
        self.assertIn("ConnectionError", h["ollama_last_error"])

    def test_successful_check_clears_last_error(self):
        m = self.load()
        with mock.patch.object(m.httpx, "get", side_effect=TimeoutError("нет ответа")):
            h1 = m.health()
        self.assertIsNotNone(h1["ollama_last_error"])

        ok = mock.Mock(status_code=200)
        with mock.patch.object(m.httpx, "get", return_value=ok):
            h2 = m.health()
        self.assertIsNone(h2["ollama_last_error"])

    def test_non_200_is_recorded_as_http_status(self):
        m = self.load()
        bad = mock.Mock(status_code=503)
        with mock.patch.object(m.httpx, "get", return_value=bad):
            h = m.health()
        self.assertEqual(h["ollama_last_error"], "HTTP 503")

    def test_no_error_before_any_check(self):
        # Состояние сразу после импорта модуля, без единого вызова _local_available() —
        # читаем переменную напрямую, не через health() (он сам бы сходил в сеть).
        m = self.load()
        self.assertIsNone(m._LOCAL_LAST_ERROR)


class RepeatedFailureDoesNotSpamLog(LocalModelHealthCase):
    def test_same_error_twice_logs_warning_once(self):
        m = self.load()
        with mock.patch.object(m.httpx, "get", side_effect=ConnectionError("туннель лёг")):
            with self.assertLogs(m.log, level="WARNING") as cap:
                m._local_available()
                m._local_available()
        warnings = [r for r in cap.records if r.levelname == "WARNING"]
        self.assertEqual(len(warnings), 1, cap.output)


if __name__ == "__main__":
    unittest.main()
