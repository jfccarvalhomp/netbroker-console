#!/usr/bin/env python3
"""NetBroker Console entry point for Ubuntu Server 22.04/24.04 amd64."""

from __future__ import annotations

import argparse
import os
import socket
from pathlib import Path

from netbroker_console.application.services import NetBrokerService
from netbroker_console.infrastructure.persistence import JsonStateRepository
from netbroker_console.presentation.http import NetBrokerServer


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = APP_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NetBroker Console web server.")
    parser.add_argument("--host", default=os.environ.get("NETBROKER_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NETBROKER_PORT", "8080")))
    parser.add_argument("--data", default=os.environ.get("NETBROKER_DATA", str(DEFAULT_DATA_DIR / "state.json")))
    return parser.parse_args()


def build_server(host: str, port: int, data_path: Path) -> NetBrokerServer:
    repository = JsonStateRepository(data_path)
    service = NetBrokerService(repository)
    return NetBrokerServer((host, port), service, APP_ROOT)


def main() -> int:
    args = parse_args()
    data_path = Path(args.data)
    server = build_server(args.host, args.port, data_path)
    socket.setdefaulttimeout(30)
    print(f"NetBroker Console listening on http://{args.host}:{args.port}")
    print(f"Data file: {data_path.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
