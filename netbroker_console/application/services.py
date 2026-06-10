from __future__ import annotations

import random

from netbroker_console.domain.canonical import (
    canonicalize_vendor_payload,
    filter_devices,
    iso_now,
    now_label,
)


class NetBrokerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def health(self) -> dict:
        return {"status": "ok", "service": "netbroker-console", "time": iso_now()}

    def get_state(self) -> dict:
        return self.repository.read()

    def list_devices(self, vendor: str = "Todos", term: str = "") -> dict:
        state = self.repository.read()
        return {"devices": filter_devices(state["devices"], vendor, term)}

    def list_alarms(self) -> dict:
        return {"alarms": self.repository.read()["alarms"]}

    def acknowledge_alarms(self, ids: list[int]) -> dict:
        selected = {int(item) for item in ids}

        def ack(state: dict) -> None:
            state["alarms"] = [alarm for alarm in state["alarms"] if int(alarm["id"]) not in selected]
            state["events"].insert(0, [now_label(), f"{len(selected)} alarme(s) reconhecido(s) pelo NOC"])
            state["events"] = state["events"][:8]

        return self.repository.update(ack)

    def run_job(self, queue: str) -> dict:
        command_queue = str(queue or "job.manual")

        def run(state: dict) -> None:
            state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
            state["events"].insert(0, [now_label(), f"Comando publicado em {command_queue}"])
            state["events"] = state["events"][:8]

        return self.repository.update(run)

    def simulate_telemetry(self) -> dict:
        def tick(state: dict) -> None:
            for device in state["devices"]:
                if device["status"] != "DOWN":
                    device["cpu"] = max(8, min(92, int(device["cpu"]) + random.randint(-8, 8)))
                    device["status"] = "ALERTA" if int(device["cpu"]) > 72 else "UP"
            state["queueDepth"] = int(state.get("queueDepth", 0)) + random.randint(30, 150)
            state["events"].insert(0, [now_label(), "Telemetria coletada e normalizada pelos adaptadores"])
            state["events"] = state["events"][:8]

        return self.repository.update(tick)

    def convert_payload(self, payload: dict) -> dict:
        return canonicalize_vendor_payload(payload)

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

