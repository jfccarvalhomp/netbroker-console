# Changelog

## 0.1.0 - 2026-06-10

- Added web frontend for the NetBroker multivendor network management console.
- Added Python backend with REST endpoints for state, devices, alarms, jobs, telemetry simulation, canonical conversion, health checks, and Prometheus-style metrics.
- Added Ubuntu systemd installer for Ubuntu Server 22.04/24.04 amd64.
- Added extracted architecture diagrams as frontend assets.
- Added Windows helper script for local validation.

## 0.2.0 - 2026-06-10

- Refactored the backend into Layered Architecture boundaries aligned with the TCC: presentation, application, domain, and infrastructure.
- Kept `server.py` as the deployment entry point for systemd.
- Updated the Ubuntu installer to deploy the Python package modules.
