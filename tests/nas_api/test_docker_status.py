"""DP-2 (2026-10-09): Docker из API — только чтение через статусный HTTP-прокси.

Карточка ведущего: nas-dp2-api-readonly-20261009.

Проверяется:
* `system_info.docker_ps_json` делает один HTTP GET на `settings.docker_status_url`
  + `/containers/json` с `params={"all": "1"}`, `timeout=10.0`,
  `trust_env=False`, `follow_redirects=False`, без UDS-транспорта;
* нормализация Names/Id/Status/Image/State → name/status/image/state сохранена
  (ведущий `/` срезается, при пустых Names берётся Id[:12]);
* любая недоступность — сеть, HTTP-статус, невалидный JSON, payload не список,
  битый элемент — HTTPException 503 «Docker status unavailable»; пустой список
  и откат на UNIX-сокет/`docker ps` не используются. До DP-2 сбой возвращал `[]`
  и выглядел как зелёный отчёт «проблемных: 0»;
* `actions._docker_post` — управление Docker отключено: сразу 503 без HTTP-запроса,
  имя хелпера сохранено (его мокает tests/nas_api/test_api_access.py);
* семья по-прежнему получает 403 на restart (авторизация/whitelist не тронуты);
* недоступный Docker в сводном статусе семьи — `unknown`, а не зелёное.

Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"

STATUS_PROXY_URL = "http://docker-status-proxy:2375"


def load_app(**env):
    """Та же конвенция, что в tests/nas_api/test_api_access.py.

    Подмена окружения + чистка sys.modules перед импортом `app.*`: иначе тест
    получит приложение (и его `settings`), собранное с чужим окружением.
    Копия, а не импорт соседнего модуля: у tests/nas_api нет гарантированного
    пакета, и импорт зависел бы от режима collection в pytest.

    DOCKER_STATUS_URL=... можно передать именованным аргументом.
    """
    tmp = tempfile.mkdtemp()
    base = {
        "LOG_FILE": os.path.join(tmp, "api.jsonl"),
        "JWT_SECRET": "test-secret",
        "NEXTCLOUD_ADMIN_USER": "admin",
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "API_OWNERS": "alexey",
        "API_CORS_ORIGINS": "",
    }
    base.update(env)
    os.environ.update(base)
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    main = importlib.import_module("app.main")
    auth = importlib.import_module("app.routers.auth")
    return main, auth


def run_coro(coro):
    """Прогнать корутину без pytest-asyncio: своя петля на вызов."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeResponse:
    """Мини-ответ с методами, которые использует docker_ps_json."""

    def __init__(self, status_code=200, payload=None, json_error=None):
        self.status_code = status_code
        self.payload = payload
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "HTTP %d" % self.status_code,
                request=httpx.Request("GET", STATUS_PROXY_URL + "/containers/json"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


def fake_client(response=None, error=None):
    """Замена httpx.AsyncClient: запоминает конструктор и GET-вызовы.

    Возвращает (класс, created, calls). created — kwargs каждого
    AsyncClient(...) (по ним видно timeout/trust_env/follow_redirects и
    отсутствие uds-транспорта), calls — список (url, params).
    """
    created = []
    calls = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            created.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            calls.append((url, params))
            if error is not None:
                raise error
            return response

    return FakeAsyncClient, created, calls


VALID_PAYLOAD = [
    {
        "Names": ["/homecloud_nasa_api"],
        "Id": "abcdef1234567890",
        "Status": "Up 2 hours (healthy)",
        "Image": "homecloud_nasa_api:latest",
        "State": "running",
    },
    {
        "Id": "fedcba654321ffff",
        "Status": "Exited (0) 3 hours ago",
        "Image": "homecloud_old:1",
        "State": "exited",
    },
    {
        "Names": [],
        "Id": "00998877665544332211",
        "Status": "Created",
        "Image": "homecloud_new:2",
        "State": "created",
    },
]

EXPECTED_NORMALIZED = [
    {
        "name": "homecloud_nasa_api",
        "status": "Up 2 hours (healthy)",
        "image": "homecloud_nasa_api:latest",
        "state": "running",
    },
    {
        "name": "fedcba654321",
        "status": "Exited (0) 3 hours ago",
        "image": "homecloud_old:1",
        "state": "exited",
    },
    {
        "name": "009988776655",
        "status": "Created",
        "image": "homecloud_new:2",
        "state": "created",
    },
]


class DockerStatusProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = dict(os.environ)
        cls.main, cls.auth = load_app()
        cls.config = importlib.import_module("app.config")
        cls.system_info = importlib.import_module("app.services.system_info")
        from fastapi.testclient import TestClient
        cls.client = TestClient(cls.main.app, raise_server_exceptions=False)
        cls.family = {"Authorization": "Bearer " + cls.auth._create_token("olga")[0]}
        cls.owner = {"Authorization": "Bearer " + cls.auth._create_token("alexey")[0]}

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls._env)

    # ── helpers ────────────────────────────────────────────────────────────────

    def call_status(self, response=None, error=None):
        client_cls, created, calls = fake_client(response=response, error=error)
        with mock.patch("httpx.AsyncClient", client_cls):
            result = run_coro(self.system_info.docker_ps_json())
        return result, created, calls

    def assert_unavailable(self, response=None, error=None):
        """503 «Docker status unavailable», ровно одна HTTP-попытка, без откатов."""
        client_cls, created, calls = fake_client(response=response, error=error)
        with mock.patch("httpx.AsyncClient", client_cls), \
                mock.patch("asyncio.create_subprocess_exec") as subproc:
            with self.assertRaises(HTTPException) as ctx:
                run_coro(self.system_info.docker_ps_json())
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, "Docker status unavailable")
        self.assertEqual(len(calls), 1, "ровно одна HTTP-попытка, без отката на сокет")
        self.assertNotIn("transport", created[0], "UDS-транспорт не используется")
        subproc.assert_not_called()

    # ── docker_ps_json: HTTP-путь и нормализация ───────────────────────────────

    def test_uses_status_proxy_get_all_without_uds(self):
        result, created, calls = self.call_status(response=FakeResponse(200, VALID_PAYLOAD))
        self.assertEqual(self.config.settings.docker_status_url, STATUS_PROXY_URL)
        self.assertEqual(calls, [(STATUS_PROXY_URL + "/containers/json", {"all": "1"})])
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].get("timeout"), 10.0)
        self.assertIs(created[0].get("trust_env"), False)
        self.assertIs(created[0].get("follow_redirects"), False)
        self.assertNotIn("transport", created[0])
        self.assertEqual(result, EXPECTED_NORMALIZED)

    def test_normalization_preserves_previous_field_contract(self):
        result, _, _ = self.call_status(response=FakeResponse(200, VALID_PAYLOAD))
        self.assertEqual(result, EXPECTED_NORMALIZED)
        for item in result:
            self.assertEqual(sorted(item), ["image", "name", "state", "status"])

    def test_genuinely_empty_list_is_allowed(self):
        # [] — законный ответ только когда контейнеров правда нет; сбой — 503.
        result, _, _ = self.call_status(response=FakeResponse(200, []))
        self.assertEqual(result, [])

    # ── docker_ps_json: любая недоступность → 503, без откатов ────────────────

    def test_network_failure_is_503_not_empty_list(self):
        self.assert_unavailable(error=httpx.ConnectError("connection refused"))

    def test_http_error_status_is_503(self):
        self.assert_unavailable(response=FakeResponse(500, {"message": "boom"}))

    def test_invalid_json_is_503(self):
        self.assert_unavailable(
            response=FakeResponse(200, json_error=json.JSONDecodeError("bad json", "", 0))
        )

    def test_non_list_payload_is_503(self):
        self.assert_unavailable(response=FakeResponse(200, {"message": "ожидался список"}))
        self.assert_unavailable(response=FakeResponse(200, None))

    def test_malformed_items_are_503(self):
        for payload in (
            ["not-an-object"],
            [{"Names": "homecloud_x"}],
            [{"Names": [7]}],
            [{"Names": [], "Id": 12345}],
            [{"Names": []}],
        ):
            with self.subTest(payload=payload):
                self.assert_unavailable(response=FakeResponse(200, payload))

    # ── управление Docker отключено (DP-2) ─────────────────────────────────────

    def test_owner_restart_is_503_and_docker_untouched(self):
        actions = importlib.import_module("app.routers.actions")
        self.assertTrue(hasattr(actions, "_docker_post"),
                        "имя хелпера мокает tests/nas_api/test_api_access.py")
        self.assertFalse(hasattr(actions, "_SOCKET"),
                         "UNIX-сокет больше не объявляется")
        client_cls, created, calls = fake_client(response=FakeResponse(200, []))
        with mock.patch("httpx.AsyncClient", client_cls), \
                mock.patch("asyncio.create_subprocess_exec") as subproc:
            r = self.client.post(
                "/v1/actions/containers/homecloud_nextcloud_db/restart",
                headers=self.owner,
            )
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json().get("detail"),
                         "Docker control disabled: read-only status proxy")
        self.assertEqual(created, [], "управление Docker не ходит никуда по HTTP")
        self.assertEqual(calls, [])
        subproc.assert_not_called()

    def test_family_restart_is_still_403_without_docker_call(self):
        actions = importlib.import_module("app.routers.actions")
        with mock.patch.object(actions, "_docker_post") as docker_helper, \
                mock.patch("httpx.AsyncClient") as http_cls:
            r = self.client.post(
                "/v1/actions/containers/homecloud_nextcloud_db/restart",
                headers=self.family,
            )
        self.assertEqual(r.status_code, 403)
        docker_helper.assert_not_called()
        http_cls.assert_not_called()

    def test_docker_post_helper_refuses_immediately(self):
        actions = importlib.import_module("app.routers.actions")
        client_cls, created, calls = fake_client(response=FakeResponse(200, []))
        with mock.patch("httpx.AsyncClient", client_cls), \
                mock.patch("asyncio.create_subprocess_exec") as subproc:
            with self.assertRaises(HTTPException) as ctx:
                run_coro(actions._docker_post("containers/homecloud_nasa_api/restart?t=10"))
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail,
                         "Docker control disabled: read-only status proxy")
        self.assertEqual(created, [])
        self.assertEqual(calls, [])
        subproc.assert_not_called()

    # ── сводный статус семьи ───────────────────────────────────────────────────

    def test_health_report_is_unknown_not_green_when_docker_is_down(self):
        health = importlib.import_module("app.services.home_health")
        client_cls, _, calls = fake_client(error=httpx.ConnectError("private detail"))
        with mock.patch("httpx.AsyncClient", client_cls), \
                mock.patch.object(health.checks, "storage_problems", new=mock.AsyncMock(return_value=([], []))), \
                mock.patch.object(health, "_check_hdd_mount", new=mock.AsyncMock(return_value=None)), \
                mock.patch.object(health, "_check_failed_units", new=mock.AsyncMock(return_value=None)), \
                mock.patch.object(health, "_read_active_alerts", return_value=[]):
            report = run_coro(health.build_health())
        self.assertTrue(calls)
        self.assertIn("Не удалось проверить", report)
        self.assertNotIn("✅", report)
        self.assertNotIn("private detail", report)

    def test_family_container_endpoint_uses_proxy(self):
        client_cls, _, calls = fake_client(response=FakeResponse(200, VALID_PAYLOAD))
        with mock.patch("httpx.AsyncClient", client_cls):
            response = self.client.get("/v1/containers", headers=self.family)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(calls)
        self.assertTrue(response.json()["containers"])

    def test_container_endpoint_unavailable_is_503(self):
        client_cls, _, _ = fake_client(error=httpx.ConnectError("private detail"))
        with mock.patch("httpx.AsyncClient", client_cls):
            response = self.client.get("/v1/containers", headers=self.family)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private detail", response.text)


class TrailingSlashInStatusUrl(unittest.TestCase):
    """docker_status_url со слэшем на конце не даёт двойного слэша в пути."""

    @classmethod
    def setUpClass(cls):
        cls._env = dict(os.environ)
        cls.main, cls.auth = load_app(DOCKER_STATUS_URL="http://nas-docker-status:2375/")
        cls.config = importlib.import_module("app.config")
        cls.system_info = importlib.import_module("app.services.system_info")

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls._env)

    def test_trailing_slash_is_stripped(self):
        self.assertEqual(self.config.settings.docker_status_url,
                         "http://nas-docker-status:2375/")
        client_cls, _, calls = fake_client(response=FakeResponse(200, []))
        with mock.patch("httpx.AsyncClient", client_cls):
            result = run_coro(self.system_info.docker_ps_json())
        self.assertEqual(calls, [("http://nas-docker-status:2375/containers/json",
                                  {"all": "1"})])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
