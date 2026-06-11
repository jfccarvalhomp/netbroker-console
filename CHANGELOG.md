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

## 0.3.0 - 2026-06-11

- Added optional PostgreSQL persistence repository for the infrastructure layer.
- Added Ubuntu setup script to install PostgreSQL, create database credentials, and enable the PostgreSQL store through systemd environment configuration.
- Kept JSON persistence as the default fallback for demos and local validation.

## 0.4.0 - 2026-06-11

- Added optional RabbitMQ broker integration for asynchronous automation jobs.
- Added a worker process that consumes RabbitMQ queues and simulates multivendor adapter processing.
- Added Ubuntu setup script and systemd worker service for RabbitMQ.

## 0.5.0 - 2026-06-11

- Added a formal multivendor adapter registry for Cisco, Fortinet, Aruba, Juniper, Huawei, and Mikrotik.
- Added `/api/adapters` to expose adapter capabilities and supported queues.
- Updated the RabbitMQ worker to process commands through adapter contracts instead of hard-coded queue logic.

## 0.6.0 - 2026-06-11

- Added local bootstrap authentication with HTTP-only session cookies.
- Added initial RBAC roles: admin, noc, auditor, and readonly.
- Protected API routes and frontend access behind login.

## 0.7.0 - 2026-06-11

- Added optional LDAP/Active Directory authentication provider.
- Added LDAP group-to-RBAC role mapping through environment configuration.
- Added Ubuntu setup script for LDAP dependencies and service environment configuration.
