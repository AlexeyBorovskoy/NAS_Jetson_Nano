"""Talk-бот обязан предъявлять шлюзу сервисный токен (A3, аудит 2026-09-19).

История дефекта: W0.2 добавил в шлюз проверку `X-Service-Token`, но единственный
вызывающий — Talk-бот — токен не отправлял. Включение токена на устройстве сделало бы
`@бобик` немым (401), а без токена защита не работает. Порядок выката: сначала
вызывающие умеют слать токен, потом шлюз его требует.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def _settings_cls():
    # Оба сервиса называют пакет `app` — свой сервис обязан стоять первым.
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    from app.config import Settings
    return Settings


class LlmHeaders(unittest.TestCase):
    def test_token_is_sent_when_configured(self):
        s = _settings_cls()(_env_file=None, llm_gateway_service_token="s3cret")
        self.assertEqual(s.llm_headers(), {"X-Service-Token": "s3cret"})

    def test_no_header_without_token(self):
        s = _settings_cls()(_env_file=None, llm_gateway_service_token="")
        self.assertEqual(s.llm_headers(), {})

    def test_every_gateway_call_in_bot_sends_headers(self):
        src = (API / "app" / "routers" / "talk_bot.py").read_text(encoding="utf-8")
        calls = re.findall(r"client\.post\((?:settings\.talk_bot_llm_url|url)\b[^)]*\)", src)
        self.assertGreaterEqual(len(calls), 2, calls)
        for call in calls:
            self.assertIn("headers=settings.llm_headers()", call, call)


if __name__ == "__main__":
    unittest.main()
