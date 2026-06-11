from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    vendor: str
    command: str
    message: str
    discovered_device: dict | None = None
    backup_completed: bool = False


class VendorAdapter:
    vendor = "Generic"
    protocols: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    queues: tuple[str, ...] = ()

    def supports(self, queue: str) -> bool:
        return queue in self.queues

    def execute(self, queue: str, payload: dict) -> AdapterResult:
        if queue == "device.discovery":
            return self.discover(payload)
        if queue == "inventory.sync":
            return self.sync_inventory(payload)
        if queue == "config.backup":
            return self.backup_config(payload)
        if queue == "alarm.remediate":
            return self.remediate_alarm(payload)
        return AdapterResult(self.name, self.vendor, queue, f"{self.name} ignorou comando desconhecido")

    @property
    def name(self) -> str:
        return f"{self.vendor} Adapter"

    def describe(self) -> dict:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "protocols": list(self.protocols),
            "platforms": list(self.platforms),
            "queues": list(self.queues),
        }

    def discover(self, payload: dict) -> AdapterResult:
        return AdapterResult(self.name, self.vendor, "device.discovery", f"{self.name} executou descoberta")

    def sync_inventory(self, payload: dict) -> AdapterResult:
        return AdapterResult(self.name, self.vendor, "inventory.sync", f"{self.name} normalizou inventario")

    def backup_config(self, payload: dict) -> AdapterResult:
        return AdapterResult(
            self.name,
            self.vendor,
            "config.backup",
            f"{self.name} gerou backup de configuracao",
            backup_completed=True,
        )

    def remediate_alarm(self, payload: dict) -> AdapterResult:
        return AdapterResult(self.name, self.vendor, "alarm.remediate", f"{self.name} aplicou playbook de remediacao")


class CiscoAdapter(VendorAdapter):
    vendor = "Cisco"
    protocols = ("REST", "NETCONF", "SSH")
    platforms = ("IOS", "IOS-XE", "NX-OS")
    queues = ("device.discovery", "inventory.sync", "config.backup", "alarm.remediate")

    def discover(self, payload: dict) -> AdapterResult:
        return AdapterResult(
            self.name,
            self.vendor,
            "device.discovery",
            "Cisco Adapter descobriu switch via NETCONF",
            discovered_device={
                "host": "SW-LAB-CISCO-01",
                "ip": "10.99.0.10",
                "vendor": "Cisco",
                "model": "Catalyst 9300",
                "site": "Lab Adapter",
                "status": "UP",
                "cpu": 22,
                "backup": "Nunca",
            },
        )


class FortinetAdapter(VendorAdapter):
    vendor = "Fortinet"
    protocols = ("REST API",)
    platforms = ("FortiGate", "FortiManager")
    queues = ("inventory.sync", "config.backup", "alarm.remediate")


class ArubaAdapter(VendorAdapter):
    vendor = "Aruba"
    protocols = ("REST API",)
    platforms = ("Aruba Central", "Aruba CX")
    queues = ("device.discovery", "inventory.sync", "config.backup")

    def discover(self, payload: dict) -> AdapterResult:
        return AdapterResult(
            self.name,
            self.vendor,
            "device.discovery",
            "Aruba Adapter descobriu access point via Aruba Central",
            discovered_device={
                "host": "AP-LAB-ARUBA-01",
                "ip": "10.99.0.21",
                "vendor": "Aruba",
                "model": "AP-515",
                "site": "Lab Adapter",
                "status": "UP",
                "cpu": 18,
                "backup": "Nunca",
            },
        )


class JuniperAdapter(VendorAdapter):
    vendor = "Juniper"
    protocols = ("NETCONF", "REST")
    platforms = ("JunOS", "Mist")
    queues = ("inventory.sync", "config.backup", "alarm.remediate")


class HuaweiAdapter(VendorAdapter):
    vendor = "Huawei"
    protocols = ("NETCONF", "SSH")
    platforms = ("VRP", "CloudEngine")
    queues = ("inventory.sync", "config.backup")


class MikrotikAdapter(VendorAdapter):
    vendor = "Mikrotik"
    protocols = ("RouterOS API", "SSH")
    platforms = ("RouterOS",)
    queues = ("device.discovery", "inventory.sync", "config.backup", "alarm.remediate")

    def discover(self, payload: dict) -> AdapterResult:
        return AdapterResult(
            self.name,
            self.vendor,
            "device.discovery",
            "Mikrotik Adapter descobriu roteador via RouterOS API",
            discovered_device={
                "host": "RTR-LAB-MKT-01",
                "ip": "10.99.0.31",
                "vendor": "Mikrotik",
                "model": "CCR2004",
                "site": "Lab Adapter",
                "status": "UP",
                "cpu": 29,
                "backup": "Nunca",
            },
        )


class AdapterRegistry:
    def __init__(self, adapters: list[VendorAdapter] | None = None) -> None:
        self.adapters = adapters or [
            CiscoAdapter(),
            FortinetAdapter(),
            ArubaAdapter(),
            JuniperAdapter(),
            HuaweiAdapter(),
            MikrotikAdapter(),
        ]

    def describe(self) -> list[dict]:
        return [adapter.describe() for adapter in self.adapters]

    def for_queue(self, queue: str) -> list[VendorAdapter]:
        return [adapter for adapter in self.adapters if adapter.supports(queue)]

    def execute(self, queue: str, payload: dict | None = None) -> list[AdapterResult]:
        supported = self.for_queue(queue)
        if not supported:
            supported = [VendorAdapter()]
        return [adapter.execute(queue, payload or {}) for adapter in supported]

