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

## Web Access

```text
http://SERVER_IP:8080/
```

## API Checks

```bash
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/state
curl http://127.0.0.1:8080/metrics
```

## Reverse Proxy Recommendation

For production exposure, place Nginx in front of the application and terminate TLS there. Keep the Python service bound to an internal port when the server is internet-facing.

