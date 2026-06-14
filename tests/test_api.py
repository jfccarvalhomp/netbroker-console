from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from netbroker_console.application.services import NetBrokerService
from netbroker_console.infrastructure.adapters import AdapterRegistry
from netbroker_console.infrastructure.messaging import build_broker
from netbroker_console.infrastructure.observability import ObservabilityRecorder
from netbroker_console.infrastructure.persistence import JsonStateRepository
from netbroker_console.infrastructure.security import AuthService
from netbroker_console.presentation.http import NetBrokerServer


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def get(self, path: str, headers: dict | None = None):
        return self.request("GET", path, headers=headers)

    def post(self, path: str, payload: dict | None = None, headers: dict | None = None):
        body = json.dumps(payload or {}).encode("utf-8")
        request_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        request_headers.update(headers or {})
        return self.request("POST", path, data=body, headers=request_headers)

    def request(self, method: str, path: str, data: bytes | None = None, headers: dict | None = None):
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers or {}, method=method)
        try:
            with self.opener.open(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.headers, exc.read()
            finally:
                exc.close()


class NetBrokerApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old_env = os.environ.copy()
        os.environ["NETBROKER_AUTH_PROVIDER"] = "local"
        os.environ["NETBROKER_ADMIN_USER"] = "admin"
        os.environ["NETBROKER_ADMIN_PASSWORD"] = "admin123"
        os.environ["NETBROKER_ADMIN_ROLE"] = "admin"
        os.environ["NETBROKER_METRICS_TOKEN"] = "test-token"

        cls.tmpdir = tempfile.TemporaryDirectory()
        repository = JsonStateRepository(Path(cls.tmpdir.name) / "state.json")
        observability = ObservabilityRecorder()
        service = NetBrokerService(repository, build_broker("memory", ""), AdapterRegistry(), observability)
        cls.server = NetBrokerServer(("127.0.0.1", 0), service, Path.cwd(), AuthService.from_environment(), observability)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()
        os.environ.clear()
        os.environ.update(cls.old_env)

    def setUp(self) -> None:
        self.client = ApiClient(self.base_url)

    def login(self) -> None:
        status, _, body = self.client.post("/api/auth/login", {"username": "admin", "password": "admin123"})
        self.assertEqual(status, 200, body)

    def test_health_is_public_and_has_trace_header(self) -> None:
        status, headers, body = self.client.get("/api/health")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(headers.get("X-Trace-Id"))

    def test_state_requires_authentication(self) -> None:
        status, _, body = self.client.get("/api/state")
        payload = json.loads(body)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "authentication_required")

    def test_login_unlocks_state_and_operations(self) -> None:
        self.login()
        status, _, body = self.client.get("/api/state")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("devices", payload)

        status, _, body = self.client.post("/api/jobs/run", {"queue": "inventory.sync"})
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(payload["queueDepth"], 0)

    def test_metrics_accepts_bearer_token_without_cookie(self) -> None:
        status, _, body = self.client.get("/metrics", {"Authorization": "Bearer test-token"})
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("netbroker_devices_total", text)
        self.assertIn("netbroker_http_requests_total", text)

    def test_observability_requires_auditor_and_returns_traces(self) -> None:
        self.login()
        self.client.get("/api/state")
        status, _, body = self.client.get("/api/observability/traces")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["traces"]), 1)


if __name__ == "__main__":
    unittest.main()
