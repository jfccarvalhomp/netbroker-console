#!/usr/bin/env python3
"""RabbitMQ worker that simulates multivendor adapters processing brokered jobs."""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

from netbroker_console.domain.canonical import now_label
from netbroker_console.infrastructure.adapters import AdapterRegistry
from netbroker_console.infrastructure.persistence import JsonStateRepository, PostgresStateRepository


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = APP_ROOT / "data"
DEFAULT_QUEUES = "device.discovery,inventory.sync,config.backup,alarm.remediate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NetBroker RabbitMQ worker.")
    parser.add_argument("--store", choices=("json", "postgres"), default=os.environ.get("NETBROKER_STORE", "json"))
    parser.add_argument("--data", default=os.environ.get("NETBROKER_DATA", str(DEFAULT_DATA_DIR / "state.json")))
    parser.add_argument("--postgres-dsn", default=os.environ.get("NETBROKER_POSTGRES_DSN", ""))
    parser.add_argument("--rabbitmq-url", default=os.environ.get("NETBROKER_RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672/%2f"))
    parser.add_argument("--exchange", default=os.environ.get("NETBROKER_RABBITMQ_EXCHANGE", "netbroker.commands"))
    parser.add_argument("--queues", default=os.environ.get("NETBROKER_WORKER_QUEUES", DEFAULT_QUEUES))
    return parser.parse_args()


def build_repository(store: str, data_path: Path, postgres_dsn: str):
    if store == "postgres":
        return PostgresStateRepository(postgres_dsn)
    return JsonStateRepository(data_path)


def record_processed(repository, registry: AdapterRegistry, queue: str, payload: dict) -> None:
    results = registry.execute(queue, payload)

    def update(state: dict) -> None:
        for result in reversed(results):
            state["events"].insert(0, [now_label(), f"{result.message} via RabbitMQ"])

            if result.discovered_device:
                known_hosts = {device["host"] for device in state["devices"]}
                if result.discovered_device["host"] not in known_hosts:
                    state["devices"].append(result.discovered_device)

            if result.backup_completed:
                for device in state["devices"]:
                    if device["vendor"] == result.vendor and device["status"] != "DOWN":
                        device["backup"] = "Hoje"

        state["events"] = state["events"][:8]

    repository.update(update)


def main() -> int:
    args = parse_args()
    try:
        import pika
    except ImportError as exc:
        raise RuntimeError("Install python3-pika to run the RabbitMQ worker") from exc

    repository = build_repository(args.store, Path(args.data), args.postgres_dsn)
    registry = AdapterRegistry()
    queues = [queue.strip() for queue in args.queues.split(",") if queue.strip()]
    socket.setdefaulttimeout(30)

    connection = pika.BlockingConnection(pika.URLParameters(args.rabbitmq_url))
    channel = connection.channel()
    channel.exchange_declare(exchange=args.exchange, exchange_type="direct", durable=True)

    for queue in queues:
        channel.queue_declare(queue=queue, durable=True)
        channel.queue_bind(exchange=args.exchange, queue=queue, routing_key=queue)

    def callback(ch, method, properties, body) -> None:
        try:
            message = json.loads(body.decode("utf-8"))
            queue = message.get("queue") or method.routing_key
            record_processed(repository, registry, queue, message.get("payload") or {})
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            raise

    for queue in queues:
        channel.basic_consume(queue=queue, on_message_callback=callback)

    print(f"NetBroker worker consuming: {', '.join(queues)}")
    try:
        channel.start_consuming()
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
