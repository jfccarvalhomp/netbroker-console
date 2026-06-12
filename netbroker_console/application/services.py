from __future__ import annotations

import random

from netbroker_console.domain.canonical import (
    canonicalize_vendor_payload,
    filter_devices,
    iso_now,
    now_label,
)
from netbroker_console.infrastructure.adapters import AdapterRegistry


class NetBrokerService:
    def __init__(self, repository, broker=None, adapters=None) -> None:
        self.repository = repository
        self.broker = broker
        self.adapters = adapters or AdapterRegistry()

    def health(self) -> dict:
        broker_name = getattr(self.broker, "name", "memory")
        return {"status": "ok", "service": "netbroker-console", "broker": broker_name, "time": iso_now()}

    def get_state(self) -> dict:
        return self.repository.read()

    def list_devices(self, vendor: str = "Todos", term: str = "") -> dict:
        state = self.repository.read()
        return {"devices": filter_devices(state["devices"], vendor, term)}

    def list_alarms(self) -> dict:
        return {"alarms": self.repository.read()["alarms"]}

    def list_adapters(self) -> dict:
        return {"adapters": self.adapters.describe()}

    def list_audit(self, limit: int = 100) -> dict:
        state = self.repository.read()
        return {"audit": state.get("audit", [])[:limit]}

    def record_audit(self, actor: str, role: str, action: str, status: str, details: str = "") -> None:
        def write(state: dict) -> None:
            state.setdefault("audit", [])
            state["audit"].insert(
                0,
                {
                    "time": iso_now(),
                    "actor": actor or "anonymous",
                    "role": role or "none",
                    "action": action,
                    "status": status,
                    "details": details,
                },
            )
            state["audit"] = state["audit"][:200]

        self.repository.update(write)

    def acknowledge_alarms(self, ids: list[int], actor: str = "system", role: str = "system") -> dict:
        selected = {int(item) for item in ids}

        def ack(state: dict) -> None:
            state["alarms"] = [alarm for alarm in state["alarms"] if int(alarm["id"]) not in selected]
            state["events"].insert(0, [now_label(), f"{len(selected)} alarme(s) reconhecido(s) pelo NOC"])
            state["events"] = state["events"][:8]
            append_audit(state, actor, role, "alarms.ack", "success", f"ids={sorted(selected)}")

        return self.repository.update(ack)

    def run_job(self, queue: str, actor: str = "system", role: str = "system") -> dict:
        command_queue = str(queue or "job.manual")
        message = None
        if self.broker is not None:
            message = self.broker.publish_command(command_queue, {"requestedBy": "web-console"})

        def run(state: dict) -> None:
            state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
            suffix = " via RabbitMQ" if message and getattr(self.broker, "name", "") == "rabbitmq" else ""
            state["events"].insert(0, [now_label(), f"Comando publicado em {command_queue}{suffix}"])
            state["events"] = state["events"][:8]
            append_audit(state, actor, role, "jobs.run", "success", f"queue={command_queue}")

        return self.repository.update(run)

    def simulate_telemetry(self, actor: str = "system", role: str = "system") -> dict:
        def tick(state: dict) -> None:
            for device in state["devices"]:
                if device["status"] != "DOWN":
                    device["cpu"] = max(8, min(92, int(device["cpu"]) + random.randint(-8, 8)))
                    device["status"] = "ALERTA" if int(device["cpu"]) > 72 else "UP"
            state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
            state["events"].insert(0, [now_label(), "Telemetria coletada e normalizada pelos adaptadores"])
            state["events"] = state["events"][:8]
            append_audit(state, actor, role, "telemetry.simulate", "success", "manual simulation")

        return self.repository.update(tick)

    def convert_payload(self, payload: dict, actor: str = "system", role: str = "system") -> dict:
        result = canonicalize_vendor_payload(payload)
        self.record_audit(actor, role, "payload.convert", "success", f"vendor={result.get('vendor')}")
        return result

    def metrics(self) -> str:
        state = self.repository.read()
        critical = sum(1 for alarm in state["alarms"] if alarm["severity"] == "critical")
        lines = [
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
        ]
        return "\n".join(lines)


def append_audit(state: dict, actor: str, role: str, action: str, status: str, details: str = "") -> None:
    state.setdefault("audit", [])
    state["audit"].insert(
        0,
        {
            "time": iso_now(),
            "actor": actor or "anonymous",
            "role": role or "none",
            "action": action,
            "status": status,
            "details": details,
        },
    )
    state["audit"] = state["audit"][:200]
