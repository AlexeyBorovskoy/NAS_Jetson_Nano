"""Семантика отката на DeepSeek и бюджета, закрывающегося при сбое (этап C, C4/C5).

История дефектов (аудит 2026-09-19, NAS-SEC-003/004; `audit_new` G06/G07), подтверждены
исполнением на HEAD:
* любой не-200 от GigaChat, включая 401 (просроченный ключ) и отказ OAuth, превращался
  в 502 и уводил семейный вопрос ко ВТОРОМУ зарубежному провайдеру — ошибка
  конфигурации незаметно меняла, куда уходят данные;
* нечитаемый `llm_usage.json` читался как `{}` — счётчики обнулялись, лимиты
  переставали работать (fail-open).

Откат допустим только на временных сбоях: 429, 5xx, обрыв транспорта.
Run: python -m pytest tests/llm_gateway -q
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "services" / "llm-gateway"


class Base(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.tmp = tempfile.mkdtemp()
        for k in [k for k in os.environ if k.startswith(("LLM_", "GIGACHAT_", "DEEPSEEK_", "CLOUDRU_"))]:
            del os.environ[k]
        os.environ.update({
            "LLM_USAGE_FILE": os.path.join(self.tmp, "usage.json"),
            "IMAGE_OUTPUT_ROOT": os.path.join(self.tmp, "images"),
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_AUTH_KEY": "k",
            "DEEPSEEK_API_KEY": "d",
            "LLM_GIGA_FALLBACK_DEEPSEEK": "true",
        })
        if str(GW) in sys.path:
            sys.path.remove(str(GW))
        sys.path.insert(0, str(GW))
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]
        self.m = importlib.import_module("app.main")
        from fastapi.testclient import TestClient
        self.c = TestClient(self.m.app, raise_server_exceptions=False)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]


class Failover(Base):
    def giga_answers(self, status):
        resp = mock.Mock(status_code=status, text="upstream says %d" % status)
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 1}}
        return mock.patch.object(self.m.httpx, "post", return_value=resp)

    def ask(self):
        with mock.patch.object(self.m, "_gigachat_access_token", return_value="t"), \
                mock.patch.object(self.m, "_call_deepseek", return_value=("from deepseek", 2)) as ds:
            r = self.c.post("/v1/chat", json={"prompt": "вопрос", "user": "t"})
        return r, ds

    def test_no_fallback_on_auth_or_client_errors(self):
        for status in (400, 401, 403, 404, 422):
            with self.giga_answers(status):
                r, ds = self.ask()
            ds.assert_not_called()
            self.assertNotEqual(r.status_code, 200, status)

    def test_fallback_on_transient_errors(self):
        for status in (429, 500, 502, 503):
            with self.giga_answers(status):
                r, ds = self.ask()
            self.assertEqual(r.status_code, 200, status)
            self.assertEqual(r.json()["provider"], "deepseek", status)

    def test_fallback_on_transport_error(self):
        with mock.patch.object(self.m.httpx, "post", side_effect=OSError("network down")):
            r, ds = self.ask()
        self.assertEqual(r.json().get("provider"), "deepseek")

    def test_no_fallback_when_oauth_rejects_key(self):
        bad = mock.Mock(status_code=401, text="bad key")
        with mock.patch.object(self.m.httpx, "post", return_value=bad), \
                mock.patch.object(self.m, "_call_deepseek", return_value=("x", 1)) as ds:
            self.m._gigachat_token["value"] = ""
            r = self.c.post("/v1/chat", json={"prompt": "вопрос", "user": "t"})
        ds.assert_not_called()
        self.assertNotEqual(r.status_code, 200)


class BudgetFailClosed(Base):
    def test_corrupted_usage_file_refuses_instead_of_resetting(self):
        with open(os.environ["LLM_USAGE_FILE"], "w", encoding="utf-8") as fh:
            fh.write("{broken")
        with mock.patch.object(self.m, "_call_gigachat", return_value=("ok", 5)) as giga:
            r = self.c.post("/v1/chat", json={"prompt": "вопрос", "user": "t"})
        self.assertEqual(r.status_code, 503, r.text)
        giga.assert_not_called()

    def test_missing_usage_file_is_a_fresh_start(self):
        with mock.patch.object(self.m, "_call_gigachat", return_value=("ok", 5)):
            r = self.c.post("/v1/chat", json={"prompt": "вопрос", "user": "t"})
        self.assertEqual(r.status_code, 200, r.text)

    def test_usage_write_is_atomic(self):
        with mock.patch.object(self.m, "_call_gigachat", return_value=("ok", 5)):
            self.c.post("/v1/chat", json={"prompt": "вопрос", "user": "t"})
        leftovers = [f for f in os.listdir(self.tmp) if f.startswith("usage.json.")]
        self.assertEqual(leftovers, [])
        import json
        with open(os.environ["LLM_USAGE_FILE"], encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["day_tokens"], 5)


if __name__ == "__main__":
    unittest.main()
