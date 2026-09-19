"""Доступ к NAS API: аутентификация ≠ авторизация (этап C, задачи C1/C2).

История дефекта (аудит 2026-09-19, NAS-SEC-001/002, `audit_new` G03/G04):
* `/v1/status, /metrics, /containers, /logs, /talk/rooms, /talk/bot/status` отвечали 200
  без токена, `POST /v1/report/now` — без авторизации; при этом `CORS *` позволял любой
  веб-странице в браузере домочадца прочитать список комнат с участниками и логи;
* любой из 5 пользователей Nextcloud получал JWT и мог перезапустить контейнер БД —
  проверялась подпись токена, но не роль.

Инвариант проверяется по ВСЕМ маршрутам приложения: новый эндпоинт без авторизации
тест не пропустит. Публичны только проверка живости, вход и документация.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"

PUBLIC = {"/healthcheck", "/api/auth/login", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
FAMILY = {"/v1/status", "/v1/metrics", "/v1/containers", "/v1/storage", "/v1/photos/stats", "/api/auth/me"}
# всё остальное — только владелец


def load_app(**env):
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
    import importlib
    main = importlib.import_module("app.main")
    auth = importlib.import_module("app.routers.auth")
    return main, auth


def routes(app):
    # По OpenAPI-схеме, а не по app.routes: в новых FastAPI подключённые роутеры лежат
    # в app.routes обёртками без пути — первая версия теста видела 4 маршрута из 21
    # и «проходила», ничего не проверяя.
    out = []
    for path, ops in app.openapi()["paths"].items():
        for m in ops:
            if m.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                out.append((m.upper(), path))
    return out


def concrete(path):
    return (path.replace("{token}", "abc123").replace("{username}", "olga")
                .replace("{name}", "homecloud_nextcloud_db"))


class AccessMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = dict(os.environ)
        cls.main, cls.auth = load_app()
        from fastapi.testclient import TestClient
        cls.client = TestClient(cls.main.app, raise_server_exceptions=False)
        cls.family = {"Authorization": "Bearer " + cls.auth._create_token("olga")[0]}
        cls.owner = {"Authorization": "Bearer " + cls.auth._create_token("alexey")[0]}
        cls.admin = {"Authorization": "Bearer " + cls.auth._create_token("admin")[0]}

    @classmethod
    def tearDownClass(cls):
        os.environ.clear()
        os.environ.update(cls._env)

    def call(self, method, path, headers=None):
        # Бэкенды (docker, Nextcloud) не нужны: проверяется только решение о доступе.
        with mock.patch("httpx.AsyncClient.send", side_effect=RuntimeError("no network in tests")), \
                mock.patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("no exec in tests")):
            return self.client.request(method, concrete(path), headers=headers or {},
                                       json={"message": "t", "username": "u", "password": "p"})

    def test_route_inventory_is_not_empty(self):
        # Тест доступа бессмыслен, если не видит маршрутов (см. routes()).
        self.assertGreaterEqual(len(routes(self.main.app)), 20)

    def test_every_non_public_route_requires_token(self):
        open_routes = []
        for method, path in routes(self.main.app):
            if path in PUBLIC:
                continue
            if self.call(method, path).status_code != 401:
                open_routes.append("%s %s" % (method, path))
        self.assertEqual(open_routes, [], "открыты без токена: %s" % open_routes)

    def test_family_member_is_not_an_operator(self):
        allowed = []
        for method, path in routes(self.main.app):
            if path in PUBLIC or path in FAMILY:
                continue
            if self.call(method, path, self.family).status_code != 403:
                allowed.append("%s %s" % (method, path))
        self.assertEqual(allowed, [], "член семьи получил доступ: %s" % allowed)

    def test_family_endpoints_open_to_family(self):
        for path in FAMILY:
            r = self.call("GET", path, self.family)
            self.assertNotIn(r.status_code, (401, 403), path)

    def test_owner_passes_authorization(self):
        for method, path in routes(self.main.app):
            if path in PUBLIC:
                continue
            r = self.call(method, path, self.owner)
            self.assertNotIn(r.status_code, (401, 403), "%s %s" % (method, path))

    def test_nextcloud_admin_is_owner_so_alerts_keep_working(self):
        r = self.call("POST", "/v1/talk/notify", self.admin)
        self.assertNotIn(r.status_code, (401, 403))

    def test_family_cannot_restart_database_and_docker_is_not_touched(self):
        actions = sys.modules["app.routers.actions"]
        with mock.patch.object(actions, "_docker_post") as docker:
            r = self.client.post("/v1/actions/containers/homecloud_nextcloud_db/restart",
                                 headers=self.family)
        self.assertEqual(r.status_code, 403)
        docker.assert_not_called()

    def test_healthcheck_stays_public(self):
        self.assertEqual(self.client.get("/healthcheck").status_code, 200)

    def test_no_wildcard_cors(self):
        r = self.client.get("/healthcheck", headers={"Origin": "http://evil.example"})
        self.assertNotEqual(r.headers.get("access-control-allow-origin"), "*")


if __name__ == "__main__":
    unittest.main()
