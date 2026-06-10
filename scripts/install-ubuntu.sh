#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
APP_DIR="/opt/${APP_NAME}"
APP_USER="${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/install-ubuntu.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y python3

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

mkdir -p "${APP_DIR}" "${APP_DIR}/assets" "${APP_DIR}/data"
cp "${SOURCE_DIR}/index.html" "${APP_DIR}/"
cp "${SOURCE_DIR}/styles.css" "${APP_DIR}/"
cp "${SOURCE_DIR}/app.js" "${APP_DIR}/"
cp "${SOURCE_DIR}/server.py" "${APP_DIR}/"
cp -r "${SOURCE_DIR}/assets/." "${APP_DIR}/assets/"

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 0755 "${APP_DIR}/server.py"

cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=NetBroker Console
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=NETBROKER_HOST=0.0.0.0
Environment=NETBROKER_PORT=8080
Environment=NETBROKER_DATA=${APP_DIR}/data/state.json
ExecStart=/usr/bin/python3 ${APP_DIR}/server.py
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
systemctl enable --now "${APP_NAME}"

echo "Instalado com sucesso."
echo "Status: sudo systemctl status ${APP_NAME}"
echo "URL: http://$(hostname -I | awk '{print $1}'):8080/"
