from __future__ import annotations

from datetime import datetime, timezone


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_label() -> str:
    return datetime.now().strftime("%H:%M")


def canonicalize_vendor_payload(payload: dict) -> dict:
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


def filter_devices(devices: list[dict], vendor: str = "Todos", term: str = "") -> list[dict]:
    normalized_term = term.lower()
    rows = []
    for device in devices:
        vendor_match = vendor == "Todos" or device.get("vendor") == vendor
        haystack = " ".join(str(device.get(key, "")) for key in ("host", "ip", "vendor", "site", "model")).lower()
        if vendor_match and normalized_term in haystack:
            rows.append(device)
    return rows

