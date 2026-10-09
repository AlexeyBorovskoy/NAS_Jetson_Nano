"""DP-2: real HTTP routing, fake Docker backend; never access a Docker socket."""
import http.client
import importlib.util
from pathlib import Path
import threading
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("status_proxy", ROOT / "services/docker-status-proxy/proxy.py")
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)


class ProxyPolicy(unittest.TestCase):
    def setUp(self):
        self.server = proxy.Server(("127.0.0.1", 0), proxy.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_container_list_is_only_allowed_read(self):
        with mock.patch.object(proxy, "container_list", return_value=[]) as backend:
            for path in ("/containers/json", "/containers/json?all=1"):
                self.assertEqual(self.request("GET", path), (200, b"[]"))
            self.assertEqual(backend.call_count, 2)

    def test_other_paths_and_queries_never_reach_docker(self):
        paths = ("/info", "/version", "/containers/x/json", "/containers/x/logs",
                 "/images/json", "/events", "/containers/json?all=1&size=1",
                 "/containers/json?all=0", "/v1.45/containers/json",
                 "//containers/json", "/containers/%6ason", "/containers/json/../x")
        with mock.patch.object(proxy, "container_list") as backend:
            for path in paths:
                with self.subTest(path=path):
                    self.assertEqual(self.request("GET", path)[0], 403)
            backend.assert_not_called()

    def test_writes_and_other_methods_never_reach_docker(self):
        with mock.patch.object(proxy, "container_list") as backend:
            for method in ("POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "CONNECT", "TRACE"):
                with self.subTest(method=method):
                    self.assertEqual(self.request(method, "/containers/json")[0], 403)
            self.assertEqual(self.request("POST", "/containers/x/restart")[0], 403)
            backend.assert_not_called()

    def test_backend_failure_is_not_a_healthy_empty_list(self):
        with mock.patch.object(proxy, "container_list", side_effect=OSError("private detail")):
            status, body = self.request("GET", "/containers/json")
        self.assertEqual(status, 503)
        self.assertNotIn(b"private detail", body)


class BackendRead(unittest.TestCase):
    def test_only_required_fields_are_returned(self):
        response = mock.Mock(status=200)
        response.read.return_value = b'[{"Names":["/api"],"State":"running","Labels":{"private":"data"},"Mounts":[]}]'
        connection = mock.Mock()
        connection.getresponse.return_value = response
        with mock.patch.object(proxy, "DockerConnection", return_value=connection):
            self.assertEqual(proxy.container_list(), [{"Names": ["/api"], "State": "running"}])
        connection.request.assert_called_once_with("GET", "/containers/json?all=1")
        connection.close.assert_called_once()

    def test_bad_backend_payloads_are_rejected_and_connection_closed(self):
        for data, status in ((b"{}", 200), (b"[1]", 200), (b"bad", 200),
                             (b"[]", 500), (b"x" * (proxy.MAX_RESPONSE + 1), 200)):
            with self.subTest(status=status, length=len(data)):
                connection = mock.Mock()
                connection.getresponse.return_value = mock.Mock(status=status)
                connection.getresponse.return_value.read.return_value = data
                with mock.patch.object(proxy, "DockerConnection", return_value=connection):
                    with self.assertRaises(ValueError):
                        proxy.container_list()
                connection.close.assert_called_once()


class DeploymentPolicy(unittest.TestCase):
    def test_socket_only_in_unpublished_isolated_proxy(self):
        compose = yaml.safe_load((ROOT / "docker/compose/docker-compose.nas_jetson_nano-api.yml").read_text(encoding="utf-8"))
        api = compose["services"]["nas_jetson_nano-api"]
        gate = compose["services"]["docker-status-proxy"]
        self.assertFalse(any("docker.sock" in mount for mount in api["volumes"]))
        self.assertEqual(gate["volumes"], ["/var/run/docker.sock:/var/run/docker.sock:ro"])
        self.assertNotIn("ports", gate)
        self.assertEqual(gate["networks"], ["docker_status"])
        self.assertTrue(compose["networks"]["docker_status"]["internal"])
        self.assertEqual(api["environment"]["DOCKER_STATUS_URL"], "http://docker-status-proxy:2375")

    def test_api_user_and_privilege_restrictions(self):
        compose = yaml.safe_load((ROOT / "docker/compose/docker-compose.nas_jetson_nano-api.yml").read_text(encoding="utf-8"))
        api = compose["services"]["nas_jetson_nano-api"]
        self.assertEqual(api["user"], "10001:10001")
        self.assertEqual(api["cap_drop"], ["ALL"])
        self.assertIn("no-new-privileges:true", api["security_opt"])
        image = (ROOT / "services/nas_jetson_nano-api/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("USER 10001:10001", image)


if __name__ == "__main__":
    unittest.main()
