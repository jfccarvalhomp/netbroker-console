#!/usr/bin/env python3
"""NetBroker Console entry point for Ubuntu Server 22.04/24.04 amd64."""

from __future__ import annotations

import argparse
import os
import socket
from pathlib import Path

from netbroker_console.application.services import NetBrokerService
from netbroker_console.infrastructure.adapters import AdapterRegistry
from netbroker_console.infrastructure.messaging import build_broker
from netbroker_console.infrastructure.persistence import JsonStateRepository, PostgresStateRepository
from netbroker_console.presentation.http import NetBrokerServer


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = APP_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NetBroker Console web server.")
    parser.add_argument("--host", default=os.environ.get("NETBROKER_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NETBROKER_PORT", "8080")))
    parser.add_argument("--data", default=os.environ.get("NETBROKER_DATA", str(DEFAULT_DATA_DIR / "state.json")))
    parser.add_argument("--store", choices=("json", "postgres"), default=os.environ.get("NETBROKER_STORE", "json"))
    parser.add_argument("--postgres-dsn", default=os.environ.get("NETBROKER_POSTGRES_DSN", ""))
    parser.add_argument("--broker", choices=("memory", "rabbitmq"), default=os.environ.get("NETBROKER_BROKER", "memory"))
    parser.add_argument("--rabbitmq-url", default=os.environ.get("NETBROKER_RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672/%2f"))
    return parser.parse_args()


def build_repository(store: str, data_path: Path, postgres_dsn: str):
    if store == "postgres":
        return PostgresStateRepository(postgres_dsn)
    return JsonStateRepository(data_path)


def build_server(host: str, port: int, repository, broker) -> NetBrokerServer:
    service = NetBrokerService(repository, broker, AdapterRegistry())
    return NetBrokerServer((host, port), service, APP_ROOT)


def main() -> int:
    args = parse_args()
    data_path = Path(args.data)
    repository = build_repository(args.store, data_path, args.postgres_dsn)
    broker = build_broker(args.broker, args.rabbitmq_url)
    server = build_server(args.host, args.port, repository, broker)
    socket.setdefaulttimeout(30)
    print(f"NetBroker Console listening on http://{args.host}:{args.port}")
    print(f"Persistence store: {args.store}")
    print(f"Broker: {args.broker}")
    if args.store == "json":
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
