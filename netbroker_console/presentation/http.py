from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


class NetBrokerServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service, static_root: Path, auth, observability) -> None:
        super().__init__(address, NetBrokerHandler)
        self.service = service
        self.static_root = static_root.resolve()
        self.auth = auth
        self.observability = observability


class NetBrokerHandler(BaseHTTPRequestHandler):
    server_version = "NetBrokerConsole/0.2"

    def setup(self) -> None:
        super().setup()
        self.trace_id, self.started_at = self.server.observability.start_trace()
        self._observability_recorded = False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json(self.server.service.health())
            return

        if parsed.path == "/api/auth/me":
            user = self.current_user()
            if not user:
                self.send_json({"authenticated": False}, HTTPStatus.UNAUTHORIZED)
                return
            self.send_json({"authenticated": True, "username": user.username, "role": user.role, "provider": self.server.auth.provider_name})
            return

        if parsed.path == "/api/state":
            if not self.require_role("readonly"):
                return
            self.send_json(self.server.service.get_state())
            return

        if parsed.path == "/api/devices":
            if not self.require_role("readonly"):
                return
            query = parse_qs(parsed.query)
            vendor = (query.get("vendor") or ["Todos"])[0]
            term = (query.get("q") or [""])[0]
            self.send_json(self.server.service.list_devices(vendor, term))
            return

        if parsed.path == "/api/alarms":
            if not self.require_role("readonly"):
                return
            self.send_json(self.server.service.list_alarms())
            return

        if parsed.path == "/api/adapters":
            if not self.require_role("readonly"):
                return
            self.send_json(self.server.service.list_adapters())
            return

        if parsed.path == "/api/audit":
            if not self.require_role("auditor"):
                return
            query = parse_qs(parsed.query)
            try:
                limit = int((query.get("limit") or ["100"])[0])
            except ValueError:
                limit = 100
            self.send_json(self.server.service.list_audit(limit))
            return

        if parsed.path == "/api/observability/logs":
            if not self.require_role("auditor"):
                return
            self.send_json(self.server.service.list_logs(query_limit(parsed.query)))
            return

        if parsed.path == "/api/observability/traces":
            if not self.require_role("auditor"):
                return
            self.send_json(self.server.service.list_traces(query_limit(parsed.query)))
            return

        if parsed.path == "/metrics":
            if not self.require_role("auditor"):
                return
            self.send_text(self.server.service.metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return

        self.send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json()

        if parsed.path == "/api/auth/login":
            user = self.server.auth.authenticate(str(body.get("username", "")), str(body.get("password", "")))
            if not user:
                self.server.service.record_audit(str(body.get("username", "")), "none", "auth.login", "failure", "invalid credentials")
                self.send_json({"error": "invalid_credentials"}, HTTPStatus.UNAUTHORIZED)
                return
            token = self.server.auth.create_session(user)
            self.server.service.record_audit(user.username, user.role, "auth.login", "success", f"provider={self.server.auth.provider_name}")
            self.send_json(
                {"authenticated": True, "username": user.username, "role": user.role, "provider": self.server.auth.provider_name},
                headers=[session_cookie(token)],
            )
            return

        if parsed.path == "/api/auth/logout":
            user = self.current_user()
            if user:
                self.server.service.record_audit(user.username, user.role, "auth.logout", "success", "session destroyed")
            self.server.auth.destroy_session(self.session_token())
            self.send_json({"authenticated": False}, headers=[clear_session_cookie()])
            return

        if parsed.path == "/api/alarms/ack":
            if not self.require_role("noc"):
                return
            ids = [int(item) for item in body.get("ids", []) if str(item).isdigit()]
            user = self.current_user()
            self.send_json(self.server.service.acknowledge_alarms(ids, user.username, user.role))
            return

        if parsed.path == "/api/jobs/run":
            if not self.require_role("noc"):
                return
            user = self.current_user()
            self.send_json(self.server.service.run_job(str(body.get("queue") or "job.manual"), user.username, user.role))
            return

        if parsed.path == "/api/telemetry/simulate":
            if not self.require_role("noc"):
                return
            user = self.current_user()
            self.send_json(self.server.service.simulate_telemetry(user.username, user.role))
            return

        if parsed.path == "/api/convert":
            if not self.require_role("readonly"):
                return
            user = self.current_user()
            self.send_json(self.server.service.convert_payload(body, user.username, user.role))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}

        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return {}

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK, headers: list[tuple[str, str]] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.record_observability(status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Trace-Id", self.trace_id)
        self.send_header("Cache-Control", "no-store")
        for name, value in headers or []:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def current_user(self):
        return self.server.auth.resolve_session(self.session_token())

    def require_role(self, role: str) -> bool:
        user = self.current_user()
        if not user:
            self.server.service.record_audit("anonymous", "none", f"access.{self.command.lower()}", "denied", f"path={self.path};required={role}")
            self.send_json({"error": "authentication_required"}, HTTPStatus.UNAUTHORIZED)
            return False
        if not self.server.auth.can(user, role):
            self.server.service.record_audit(user.username, user.role, f"access.{self.command.lower()}", "forbidden", f"path={self.path};required={role}")
            self.send_json({"error": "forbidden", "requiredRole": role}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def session_token(self) -> str | None:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "netbroker_session":
                return value
        return None

    def send_text(self, text: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.record_observability(HTTPStatus.OK)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Trace-Id", self.trace_id)
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, raw_path: str) -> None:
        path = unquote(raw_path).split("?", 1)[0]
        if path in ("", "/"):
            path = "/index.html"
        if path.startswith("/"):
            path = path[1:]

        candidate = (self.server.static_root / path).resolve()
        try:
            candidate.relative_to(self.server.static_root)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        if not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type, _ = mimetypes.guess_type(candidate.name)
        body = candidate.read_bytes()
        self.record_observability(HTTPStatus.OK)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Trace-Id", self.trace_id)
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self.record_observability(int(code))
        super().send_error(code, message, explain)

    def record_observability(self, status: int) -> None:
        if self._observability_recorded:
            return
        user = self.current_user()
        actor = user.username if user else "anonymous"
        self.server.observability.record_request(
            self.trace_id,
            self.started_at,
            self.command,
            self.path,
            int(status),
            actor,
        )
        self._observability_recorded = True

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))


def session_cookie(token: str) -> tuple[str, str]:
    return (
        "Set-Cookie",
        f"netbroker_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800",
    )


def clear_session_cookie() -> tuple[str, str]:
    return (
        "Set-Cookie",
        "netbroker_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0",
    )


def query_limit(query: str) -> int:
    try:
        limit = int((parse_qs(query).get("limit") or ["100"])[0])
    except ValueError:
        return 100
    return max(1, min(limit, 500))
