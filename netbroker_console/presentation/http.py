from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


class NetBrokerServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service, static_root: Path) -> None:
        super().__init__(address, NetBrokerHandler)
        self.service = service
        self.static_root = static_root.resolve()


class NetBrokerHandler(BaseHTTPRequestHandler):
    server_version = "NetBrokerConsole/0.2"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json(self.server.service.health())
            return

        if parsed.path == "/api/state":
            self.send_json(self.server.service.get_state())
            return

        if parsed.path == "/api/devices":
            query = parse_qs(parsed.query)
            vendor = (query.get("vendor") or ["Todos"])[0]
            term = (query.get("q") or [""])[0]
            self.send_json(self.server.service.list_devices(vendor, term))
            return

        if parsed.path == "/api/alarms":
            self.send_json(self.server.service.list_alarms())
            return

        if parsed.path == "/metrics":
            self.send_text(self.server.service.metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return

        self.send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json()

        if parsed.path == "/api/alarms/ack":
            ids = [int(item) for item in body.get("ids", []) if str(item).isdigit()]
            self.send_json(self.server.service.acknowledge_alarms(ids))
            return

        if parsed.path == "/api/jobs/run":
            self.send_json(self.server.service.run_job(str(body.get("queue") or "job.manual")))
            return

        if parsed.path == "/api/telemetry/simulate":
            self.send_json(self.server.service.simulate_telemetry())
            return

        if parsed.path == "/api/convert":
            self.send_json(self.server.service.convert_payload(body))
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

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
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
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

