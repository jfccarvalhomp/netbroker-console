#!/usr/bin/env python3
"""NetBroker Console web backend for Ubuntu Server 24.04 amd64."""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import random
import socket
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = APP_ROOT / "data"


INITIAL_STATE = {
    "queueDepth": 2416,
    "devices": [
        {"host": "SW-MTZ-CORE-01", "ip": "10.10.0.2", "vendor": "Cisco", "model": "Catalyst 9500", "site": "Matriz", "status": "UP", "cpu": 34, "backup": "Hoje"},
        {"host": "RTR-MTZ-WAN-01", "ip": "10.10.0.1", "vendor": "Juniper", "model": "MX204", "site": "Matriz", "status": "UP", "cpu": 41, "backup": "Hoje"},
        {"host": "FW-DC-EDGE-01", "ip": "10.20.0.5", "vendor": "Fortinet", "model": "FortiGate 200F", "site": "Datacenter", "status": "ALERTA", "cpu": 76, "backup": "Ontem"},
        {"host": "AP-FIL-03-12", "ip": "10.31.12.9", "vendor": "Aruba", "model": "AP-515", "site": "Filial 03", "status": "UP", "cpu": 19, "backup": "Hoje"},
        {"host": "RTR-REM-07", "ip": "10.44.7.1", "vendor": "Mikrotik", "model": "CCR2004", "site": "Remoto 07", "status": "DOWN", "cpu": 0, "backup": "3 dias"},
        {"host": "SW-DC-TOR-06", "ip": "10.20.6.2", "vendor": "Cisco", "model": "Nexus 93180", "site": "Datacenter", "status": "UP", "cpu": 53, "backup": "Hoje"},
        {"host": "FW-FIL-02", "ip": "10.32.0.5", "vendor": "Fortinet", "model": "FortiGate 80F", "site": "Filial 02", "status": "UP", "cpu": 48, "backup": "Hoje"},
        {"host": "SW-FIL-05-AC", "ip": "10.35.0.2", "vendor": "Aruba", "model": "CX 6200", "site": "Filial 05", "status": "ALERTA", "cpu": 68, "backup": "Ontem"},
    ],
    "alarms": [
        {"id": 1, "severity": "critical", "device": "RTR-REM-07", "text": "Site remoto sem resposta SNMP e ICMP ha 9 minutos.", "source": "Monitoring Service"},
        {"id": 2, "severity": "warning", "device": "FW-DC-EDGE-01", "text": "CPU acima de 75% durante cinco coletas consecutivas.", "source": "Fortinet Adapter"},
        {"id": 3, "severity": "warning", "device": "SW-FIL-05-AC", "text": "Interface uplink com descarte crescente de pacotes.", "source": "Aruba Adapter"},
        {"id": 4, "severity": "info", "device": "SW-MTZ-CORE-01", "text": "Backup de configuracao concluido com sucesso.", "source": "Backup Service"},
    ],
    "jobs": [
        {"name": "Backup de configuracoes", "desc": "Coleta configs via SSH, REST ou NETCONF e persiste no PostgreSQL.", "queue": "config.backup"},
        {"name": "Descoberta multivendor", "desc": "Varre sub-redes, identifica fabricante e cria Device canonico.", "queue": "device.discovery"},
        {"name": "Atualizacao de inventario", "desc": "Normaliza interfaces, versoes e modelos para o dominio central.", "queue": "inventory.sync"},
        {"name": "Remediacao de alarme", "desc": "Executa playbooks aprovados para eventos operacionais conhecidos.", "queue": "alarm.remediate"},
    ],
    "events": [
        ["10:42", "command.config.backup publicado pelo Configuration Service"],
        ["10:43", "Cisco Adapter converteu interfaces para modelo canonico"],
        ["10:44", "Monitoring Service correlacionou alarme de CPU no FW-DC-EDGE-01"],
        ["10:45", "OpenTelemetry fechou trace distribuido do job inventory.sync"],
    ],
}


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(INITIAL_STATE)

    def read(self) -> dict:
        with self.lock:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._write(INITIAL_STATE)
                return copy.deepcopy(INITIAL_STATE)

    def update(self, mutator) -> dict:
        with self.lock:
            state = self.read()
            mutator(state)
            self._write(state)
            return state

    def _write(self, state: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize(payload: dict) -> dict:
    bandwidth = payload.get("bandwidth") or payload.get("speed")
    if isinstance(bandwidth, (int, float)):
        speed = f"{bandwidth / 1_000_000_000:g}Gbps"
    else:
        speed = str(bandwidth or "unknown")

    return {
        "deviceId": payload.get("hostname") or payload.get("device") or "unknown-device",
        "managementIp": payload.get("mgmtIp") or payload.get("ip") or "0.0.0.0",
        "vendor": payload.get("vendorName") or payload.get("vendor") or "Generic",
        "interfaceName": payload.get("ifName") or payload.get("interface") or "unknown-interface",
        "status": str(payload.get("operStatus") or payload.get("status") or "unknown").upper(),
        "speed": speed,
        "normalizedAt": iso_now(),
    }


def filter_devices(state: dict, query: dict) -> list[dict]:
    vendor = (query.get("vendor") or ["Todos"])[0]
    term = (query.get("q") or [""])[0].lower()
    rows = []
    for device in state["devices"]:
        vendor_match = vendor == "Todos" or device["vendor"] == vendor
        haystack = " ".join(str(device.get(key, "")) for key in ("host", "ip", "vendor", "site", "model")).lower()
        if vendor_match and term in haystack:
            rows.append(device)
    return rows


class NetBrokerHandler(BaseHTTPRequestHandler):
    server_version = "NetBrokerConsole/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"status": "ok", "service": "netbroker-console", "time": iso_now()})
            return

        if parsed.path == "/api/state":
            self.send_json(self.server.store.read())
            return

        if parsed.path == "/api/devices":
            state = self.server.store.read()
            self.send_json({"devices": filter_devices(state, parse_qs(parsed.query))})
            return

        if parsed.path == "/api/alarms":
            self.send_json({"alarms": self.server.store.read()["alarms"]})
            return

        if parsed.path == "/metrics":
            self.send_metrics()
            return

        self.send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json()

        if parsed.path == "/api/alarms/ack":
            ids = {int(item) for item in body.get("ids", []) if str(item).isdigit()}

            def ack(state: dict) -> None:
                state["alarms"] = [alarm for alarm in state["alarms"] if int(alarm["id"]) not in ids]
                state["events"].insert(0, [now_label(), f"{len(ids)} alarme(s) reconhecido(s) pelo NOC"])
                state["events"] = state["events"][:8]

            self.send_json(self.server.store.update(ack))
            return

        if parsed.path == "/api/jobs/run":
            queue = str(body.get("queue") or "job.manual")

            def run(state: dict) -> None:
                state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
                state["events"].insert(0, [now_label(), f"Comando publicado em {queue}"])
                state["events"] = state["events"][:8]

            self.send_json(self.server.store.update(run))
            return

        if parsed.path == "/api/telemetry/simulate":
            def tick(state: dict) -> None:
                for device in state["devices"]:
                    if device["status"] != "DOWN":
                        device["cpu"] = max(8, min(92, int(device["cpu"]) + random.randint(-8, 8)))
                        device["status"] = "ALERTA" if int(device["cpu"]) > 72 else "UP"
                state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
                state["events"].insert(0, [now_label(), "Telemetria coletada e normalizada pelos adaptadores"])
                state["events"] = state["events"][:8]

            self.send_json(self.server.store.update(tick))
            return

        if parsed.path == "/api/convert":
            self.send_json(canonicalize(body))
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

    def send_metrics(self) -> None:
        state = self.server.store.read()
        critical = sum(1 for alarm in state["alarms"] if alarm["severity"] == "critical")
        body = "\n".join([
            "# HELP netbroker_devices_total Total de dispositivos gerenciados",
            "# TYPE netbroker_devices_total gauge",
            f"netbroker_devices_total {len(state['devices'])}",
            "# HELP netbroker_alarms_critical Alarmes criticos ativos",
            "# TYPE netbroker_alarms_critical gauge",
            f"netbroker_alarms_critical {critical}",
            "# HELP netbroker_queue_depth Mensagens simuladas em fila",
            "# TYPE netbroker_queue_depth gauge",
            f"netbroker_queue_depth {int(state.get('queueDepth', 0))}",
            "",
        ]).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, raw_path: str) -> None:
        path = unquote(raw_path).split("?", 1)[0]
        if path in ("", "/"):
            path = "/index.html"
        if path.startswith("/"):
            path = path[1:]

        candidate = (APP_ROOT / path).resolve()
        try:
            candidate.relative_to(APP_ROOT)
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


class NetBrokerServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], store: Store) -> None:
        super().__init__(address, NetBrokerHandler)
        self.store = store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NetBroker Console web server.")
    parser.add_argument("--host", default=os.environ.get("NETBROKER_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NETBROKER_PORT", "8080")))
    parser.add_argument("--data", default=os.environ.get("NETBROKER_DATA", str(DEFAULT_DATA_DIR / "state.json")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = Store(Path(args.data))
    server = NetBrokerServer((args.host, args.port), store)
    socket.setdefaulttimeout(30)
    print(f"NetBroker Console listening on http://{args.host}:{args.port}")
    print(f"Data file: {Path(args.data).resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
