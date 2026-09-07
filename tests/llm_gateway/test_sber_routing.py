"""Unit tests for Sber-era LLM gateway routing (no network, no secrets).

Run from repo root (Windows):
  python -m pytest tests/llm_gateway/test_sber_routing.py -q
or:
  python tests/llm_gateway/test_sber_routing.py
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# services/llm-gateway/app on path
ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "services" / "llm-gateway"
sys.path.insert(0, str(GW))


def _reload_main(env: dict):
    """Apply env for the whole process (caller must restore) and reimport app.main."""
    os.environ.update({k: str(v) for k, v in env.items()})
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.main")


class TestSberRouting(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]

    def test_default_provider_is_gigachat(self):
        m = _reload_main(
            {
                "LLM_PROVIDER": "gigachat",
                "GIGACHAT_AUTH_KEY": "",
                "LLM_PREFER_LOCAL": "false",
            }
        )
        # FastAPI TestClient optional — call chat with empty key → mock
        from fastapi.testclient import TestClient

        client = TestClient(m.app)
        r = client.post("/v1/chat", json={"prompt": "hi", "user": "t"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["provider"], "gigachat")
        self.assertEqual(body["model"], "mock")
        self.assertIn("not configured", body["content"])

    def test_health_exposes_sber_fields(self):
        m = _reload_main(
            {
                "LLM_PROVIDER": "gigachat",
                "GIGACHAT_BASE_URL": "https://api.giga.chat/v1",
                "GIGACHAT_MODEL": "GigaChat-2",
                "LLM_GIGA_FALLBACK_DEEPSEEK": "true",
            }
        )
        from fastapi.testclient import TestClient

        client = TestClient(m.app)
        h = client.get("/health").json()
        self.assertEqual(h["provider"], "gigachat")
        self.assertIn("gigachat", h["providers"])
        self.assertIn("cloudru", h["providers"])
        self.assertTrue(h["giga_fallback_deepseek"])
        self.assertIn("api.giga.chat", h["gigachat_base"])
        self.assertEqual(h["gigachat_model"], "GigaChat-2")

    def test_giga_failover_to_deepseek(self):
        m = _reload_main(
            {
                "LLM_PROVIDER": "gigachat",
                "GIGACHAT_AUTH_KEY": "dummy",
                "DEEPSEEK_API_KEY": "sk-test",
                "LLM_GIGA_FALLBACK_DEEPSEEK": "true",
                "LLM_DAILY_TOKEN_LIMIT": "0",
                "LLM_MONTHLY_COST_LIMIT_USD": "0",
                "LLM_USER_DAILY_TOKEN_LIMIT": "0",
                "LLM_REDACT_PERSONAL_DATA": "false",
            }
        )
        from fastapi import HTTPException

        def boom(*_a, **_k):
            raise HTTPException(status_code=502, detail="giga down")

        # Call route function directly so HTTPException is not turned into a
        # response before our try/except (TestClient quirk).
        with mock.patch.object(m, "_call_gigachat", side_effect=boom):
            with mock.patch.object(m, "_call_deepseek", return_value=("ok-ds", 3)):
                out = m.chat(
                    m.ChatRequest(prompt="ping", provider="gigachat", user="t")
                )
        self.assertEqual(out.provider, "deepseek")
        self.assertEqual(out.fallback_from, "gigachat")
        self.assertEqual(out.content, "ok-ds")
        self.assertEqual(out.tokens, 3)

    def test_cloudru_mock_without_key(self):
        m = _reload_main({"CLOUDRU_FM_API_KEY": ""})
        from fastapi.testclient import TestClient

        client = TestClient(m.app)
        r = client.post(
            "/v1/chat",
            json={"prompt": "x", "provider": "cloudru", "user": "t"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["model"], "mock")

    def test_balance_requires_key(self):
        m = _reload_main({"GIGACHAT_AUTH_KEY": ""})
        from fastapi.testclient import TestClient

        client = TestClient(m.app)
        r = client.get("/v1/provider/gigachat/balance")
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
