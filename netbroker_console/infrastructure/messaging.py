from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class CommandMessage:
    queue: str
    source: str
    payload: dict
    created_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryBroker:
    name = "memory"

    def publish_command(self, queue: str, payload: dict | None = None) -> CommandMessage:
        return CommandMessage(
            queue=queue,
            source="api",
            payload=payload or {},
            created_at=utc_now(),
        )


class RabbitMQBroker:
    name = "rabbitmq"

    def __init__(self, url: str, exchange: str = "netbroker.commands") -> None:
        if not url:
            raise ValueError("RabbitMQ URL is required")
        try:
            import pika
        except ImportError as exc:
            raise RuntimeError("Install python3-pika to use RabbitMQ messaging") from exc

        self.pika = pika
        self.url = url
        self.exchange = exchange

    def publish_command(self, queue: str, payload: dict | None = None) -> CommandMessage:
        message = CommandMessage(
            queue=queue,
            source="api",
            payload=payload or {},
            created_at=utc_now(),
        )
        body = json.dumps(message.__dict__, ensure_ascii=False).encode("utf-8")

        connection = self.pika.BlockingConnection(self.pika.URLParameters(self.url))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=self.exchange, exchange_type="direct", durable=True)
            channel.queue_declare(queue=queue, durable=True)
            channel.queue_bind(exchange=self.exchange, queue=queue, routing_key=queue)
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=queue,
                body=body,
                properties=self.pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
        finally:
            connection.close()

        return message


def build_broker(kind: str, rabbitmq_url: str) -> InMemoryBroker | RabbitMQBroker:
    if kind == "rabbitmq":
        return RabbitMQBroker(rabbitmq_url)
    return InMemoryBroker()

