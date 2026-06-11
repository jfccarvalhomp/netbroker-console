#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
APP_DIR="/opt/${APP_NAME}"
APP_USER="${APP_NAME}"
ENV_FILE="/etc/${APP_NAME}.env"
WORKER_SERVICE="/etc/systemd/system/${APP_NAME}-worker.service"
RABBITMQ_URL="${NETBROKER_RABBITMQ_URL:-amqp://guest:guest@127.0.0.1:5672/%2f}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-rabbitmq-ubuntu.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y rabbitmq-server python3-pika

systemctl enable --now rabbitmq-server

touch "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

if grep -q '^NETBROKER_BROKER=' "${ENV_FILE}"; then
  sed -i 's|^NETBROKER_BROKER=.*|NETBROKER_BROKER=rabbitmq|' "${ENV_FILE}"
else
  echo "NETBROKER_BROKER=rabbitmq" >> "${ENV_FILE}"
fi

if grep -q '^NETBROKER_RABBITMQ_URL=' "${ENV_FILE}"; then
  sed -i "s|^NETBROKER_RABBITMQ_URL=.*|NETBROKER_RABBITMQ_URL=${RABBITMQ_URL}|" "${ENV_FILE}"
else
  echo "NETBROKER_RABBITMQ_URL=${RABBITMQ_URL}" >> "${ENV_FILE}"
fi

cat > "${WORKER_SERVICE}" <<SERVICE
[Unit]
Description=NetBroker RabbitMQ Worker
After=network-online.target rabbitmq-server.service ${APP_NAME}.service
Wants=network-online.target rabbitmq-server.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=NETBROKER_DATA=${APP_DIR}/data/state.json
EnvironmentFile=-/etc/${APP_NAME}.env
ExecStart=/usr/bin/python3 ${APP_DIR}/worker.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=${APP_DIR}/data

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl restart "${APP_NAME}"
systemctl enable --now "${APP_NAME}-worker"

echo "RabbitMQ configurado para ${APP_NAME}."
echo "Broker: rabbitmq"
echo "Worker: sudo systemctl status ${APP_NAME}-worker"
