# Deployment

## Target Platform

- Ubuntu Server 22.04 or 24.04
- amd64 architecture
- Python 3 from the distribution packages
- systemd

## Install

Copy the project folder to the server, then run:

```bash
cd /home/<user>/netbroker-console
sudo bash scripts/install-ubuntu.sh
```

The installer copies the application to `/opt/netbroker-console`, creates a system user, writes a systemd unit, and starts the service.

## Service Operations

```bash
sudo systemctl status netbroker-console
sudo systemctl restart netbroker-console
sudo journalctl -u netbroker-console -f
```

## Local Authentication

Default bootstrap credentials:

```text
admin / admin123
```

Set a strong password in `/etc/netbroker-console.env`:

```bash
NETBROKER_ADMIN_USER=admin
NETBROKER_ADMIN_PASSWORD=change-this-password
NETBROKER_ADMIN_ROLE=admin
```

Then restart:

```bash
sudo systemctl restart netbroker-console
```

## LDAP / Active Directory Authentication

Interactive helper:

```bash
bash scripts/configure-ldap-ubuntu.sh
```

Install LDAP support and write `/etc/netbroker-console.env`:

```bash
sudo NETBROKER_LDAP_URI="ldap://ad.example.local:389" \
  NETBROKER_LDAP_BASE_DN="DC=example,DC=local" \
  NETBROKER_LDAP_BIND_DN="CN=svc-netbroker,OU=Service Accounts,DC=example,DC=local" \
  NETBROKER_LDAP_BIND_PASSWORD="service-account-password" \
  NETBROKER_LDAP_GROUP_ROLE_MAP="CN=NetBroker Admins,OU=Groups,DC=example,DC=local=admin;CN=NetBroker NOC,OU=Groups,DC=example,DC=local=noc" \
  bash scripts/setup-ldap-ubuntu.sh
```

The application maps LDAP `memberOf` DNs to RBAC roles through `NETBROKER_LDAP_GROUP_ROLE_MAP`.

## Web Access

```text
http://SERVER_IP:8080/
```

## API Checks

```bash
curl http://127.0.0.1:8080/api/health
curl -c /tmp/netbroker.cookies \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  http://127.0.0.1:8080/api/auth/login
curl -b /tmp/netbroker.cookies http://127.0.0.1:8080/api/state
curl -b /tmp/netbroker.cookies http://127.0.0.1:8080/api/adapters
curl -b /tmp/netbroker.cookies http://127.0.0.1:8080/metrics
```

## PostgreSQL Persistence

The default install uses local JSON persistence to keep the demo easy to run. To enable PostgreSQL on Ubuntu:

```bash
sudo bash scripts/setup-postgres-ubuntu.sh
```

This installs PostgreSQL and `python3-psycopg2`, creates a database and role, writes `/etc/netbroker-console.env`, and restarts the service with:

```text
NETBROKER_STORE=postgres
NETBROKER_POSTGRES_DSN=dbname=netbroker_console user=netbroker_console password=... host=127.0.0.1 port=5432
```

## RabbitMQ Broker

To enable asynchronous job dispatch through RabbitMQ:

```bash
sudo bash scripts/setup-rabbitmq-ubuntu.sh
```

This installs RabbitMQ and `python3-pika`, enables `NETBROKER_BROKER=rabbitmq`, restarts the web service, and starts the `netbroker-console-worker` service.

Operational checks:

```bash
sudo systemctl status rabbitmq-server
sudo systemctl status netbroker-console-worker
sudo journalctl -u netbroker-console-worker -f
```

## Reverse Proxy Recommendation

For production exposure, place Nginx in front of the application and terminate TLS there. Keep the Python service bound to an internal port when the server is internet-facing.
