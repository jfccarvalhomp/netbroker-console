from __future__ import annotations

import json
import unittest
from pathlib import Path


class OpenApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract_path = Path("docs/openapi.json")
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))

    def test_contract_has_required_openapi_sections(self) -> None:
        self.assertEqual(self.contract["openapi"], "3.0.3")
        self.assertIn("info", self.contract)
        self.assertIn("paths", self.contract)
        self.assertIn("components", self.contract)

    def test_contract_documents_current_http_routes(self) -> None:
        expected_routes = {
            ("GET", "/api/health"),
            ("GET", "/api/auth/me"),
            ("GET", "/api/state"),
            ("GET", "/api/devices"),
            ("GET", "/api/alarms"),
            ("GET", "/api/adapters"),
            ("GET", "/api/audit"),
            ("GET", "/api/observability/logs"),
            ("GET", "/api/observability/traces"),
            ("GET", "/metrics"),
            ("POST", "/api/auth/login"),
            ("POST", "/api/auth/logout"),
            ("POST", "/api/alarms/ack"),
            ("POST", "/api/jobs/run"),
            ("POST", "/api/telemetry/simulate"),
            ("POST", "/api/convert"),
        }
        documented_routes = {
            (method.upper(), path)
            for path, operations in self.contract["paths"].items()
            for method in operations
        }
        self.assertEqual(documented_routes, expected_routes)

    def test_protected_routes_declare_security(self) -> None:
        public_routes = {
            ("GET", "/api/health"),
            ("POST", "/api/auth/login"),
            ("POST", "/api/auth/logout"),
        }
        for path, operations in self.contract["paths"].items():
            for method, operation in operations.items():
                route = (method.upper(), path)
                if route not in public_routes:
                    self.assertIn("security", operation, route)


if __name__ == "__main__":
    unittest.main()
