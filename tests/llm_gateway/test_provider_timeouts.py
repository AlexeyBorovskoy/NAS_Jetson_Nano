"""Stage 15: a slow fallback must fail before the bot stops waiting.

Mock transports scale provider waits; no requests leave the test process.
"""
import ast
import time
from unittest import mock

import httpx
from openai import OpenAI

from test_gateway_contract import GatewayCase, ROOT


def bot_timeout(name="talk_bot_llm_timeout"):
    tree = ast.parse((ROOT / "services/nas_jetson_nano-api/app/config.py").read_text(encoding="utf-8"))
    settings = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    field = next(node for node in settings.body if isinstance(node, ast.AnnAssign)
                 and node.target.id == name)
    return ast.literal_eval(field.value)


class ProviderTimeouts(GatewayCase):
    def test_slow_fallback_finishes_before_bot_and_does_not_retry(self):
        m = self.load()
        budgets, clients = [], []
        scale = 0.001

        def giga(url, **kwargs):
            budgets.append(kwargs["timeout"])
            time.sleep(kwargs["timeout"] * scale)
            if url.endswith("/oauth"):
                return httpx.Response(200, json={"access_token": "test", "expires_at": 0})
            return httpx.Response(503, text="temporarily unavailable")

        def slow_deepseek(request):
            timeout = request.extensions["timeout"]["read"]
            budgets.append(timeout)
            time.sleep(timeout * scale)
            raise httpx.ReadTimeout("synthetic slow provider", request=request)

        def sdk(**kwargs):
            client = OpenAI(http_client=httpx.Client(transport=httpx.MockTransport(slow_deepseek)), **kwargs)
            clients.append(client)
            self.addCleanup(client.close)
            return client

        with mock.patch.object(m.httpx, "post", side_effect=giga), mock.patch.object(m, "OpenAI", side_effect=sdk):
            response = self.client(m).post("/v1/chat", json={"prompt": "hello", "user": "test"})
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(len(budgets), 3, "OAuth + GigaChat + one DeepSeek attempt")
        self.assertLess(sum(budgets), bot_timeout())
        self.assertEqual(clients[0].max_retries, 0)
        self.assertEqual(budgets[-1], 90.0)
        self.assertTrue(clients[0].is_closed())

    def test_deepseek_timeout_can_be_overridden(self):
        m = self.load(DEEPSEEK_TIMEOUT="0.02")
        timeouts = []

        def stalled(request):
            timeouts.append(request.extensions["timeout"]["read"])
            raise httpx.ReadTimeout("synthetic timeout", request=request)

        def sdk(**kwargs):
            client = OpenAI(http_client=httpx.Client(transport=httpx.MockTransport(stalled)), **kwargs)
            self.addCleanup(client.close)
            return client

        with mock.patch.object(m, "OpenAI", side_effect=sdk):
            response = self.client(m).post("/v1/chat", json={"prompt": "hello", "provider": "deepseek"})
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(timeouts, [0.02])

    def test_oauth_uses_fifteen_second_timeout(self):
        m = self.load()
        with mock.patch.object(m.httpx, "post", side_effect=httpx.ReadTimeout("synthetic timeout")) as post:
            with self.assertRaises(m.HTTPException):
                m._gigachat_access_token()
        self.assertEqual(post.call_args.kwargs["timeout"], 15.0)

    def test_image_edit_budget_includes_three_token_refreshes(self):
        m = self.load(LLM_ALLOW_IMAGE_ANALYSIS="true")
        budgets = []

        def provider(url, **kwargs):
            budgets.append(kwargs["timeout"])
            if url.endswith("/oauth"):
                return httpx.Response(200, json={"access_token": "test", "expires_at": 1})
            if url.endswith("/files"):
                return httpx.Response(201, json={"id": "synthetic-input"})
            if url.endswith("/content"):
                return httpx.Response(200, content=b"synthetic-image")
            return httpx.Response(200, json={
                "choices": [{"message": {"content": '<img src="synthetic-output"/>'}}],
                "usage": {"total_tokens": 1},
            })

        with mock.patch.object(m.httpx, "post", side_effect=provider), \
                mock.patch.object(m.httpx, "get", side_effect=provider):
            response = self.client(m).post("/v1/image/edit", json={
                "image_base64": "ZmFrZQ==", "instruction": "draw a circle", "user": "test",
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(budgets, [15, 180, 15, 300, 15, 120])
        self.assertLess(sum(budgets), bot_timeout("talk_bot_image_timeout"))
