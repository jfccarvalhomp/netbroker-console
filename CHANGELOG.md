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

## 0.7.1 - 2026-06-12

- Added an interactive LDAP configuration helper to avoid typing long environment-variable commands manually.

## 0.8.0 - 2026-06-12

- Added action auditing for authentication, authorization failures, operational jobs, alarm acknowledgements, telemetry simulation, payload conversion, and worker processing.
- Added `/api/audit` protected by the auditor RBAC level.
- Added an audit view to the web console.

## 0.9.0 - 2026-06-12

- Added optional TACACS+ authentication provider.
- Added TACACS+ user-to-RBAC role mapping through environment configuration.
- Added Ubuntu setup and interactive configuration scripts for TACACS+.

## 0.10.0 - 2026-06-12

- Added optional Cisco ISE authorization policy layer.
- Added user, authorization profile, and SGT to RBAC mapping for ISE-oriented deployments.
- Added Ubuntu setup and interactive configuration scripts for ISE authorization.

## 0.11.0 - 2026-06-12

- Added in-memory observability recorder for HTTP logs, request traces, counters, errors, and average latency.
- Added `/api/observability/logs` and `/api/observability/traces`, protected by auditor RBAC.
- Expanded `/metrics` with HTTP request, error, and latency metrics.
- Added an Observability view to the web console.

## 0.12.0 - 2026-06-14

- Added optional bearer-token access for Prometheus scraping of `/metrics`.
- Added Ubuntu setup script for Prometheus target configuration.
- Added importable Grafana dashboard JSON for NetBroker metrics.

## 0.13.0 - 2026-06-14

- Added Ubuntu Nginx reverse-proxy setup script for production web exposure.
- Added optional Let's Encrypt TLS automation through Certbot.
- Added HTTP security headers and localhost backend binding guidance.

## 0.13.1 - 2026-06-14

- Added publication diagnostic script for DNS, public HTTP, Nginx, and local health checks.
- Documented DNS validation before running Certbot/Let's Encrypt.

## 0.14.0 - 2026-06-14

- Added Ubuntu backup script for runtime data, environment, Nginx, Prometheus, and optional PostgreSQL dump.
- Added Ubuntu restore script for operational recovery on an existing or rebuilt server.
- Documented backup and restore workflow.

## 0.15.0 - 2026-06-14

- Added GitHub Actions CI for Python compilation, shell syntax, Grafana dashboard JSON, and web asset checks.
- Added local validation script that mirrors the CI checks.
- Documented validation workflow before server deployment.
