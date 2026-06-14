#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
ENV_FILE="/etc/${APP_NAME}.env"
NGINX_SITE="/etc/nginx/sites-available/${APP_NAME}"
NGINX_LINK="/etc/nginx/sites-enabled/${APP_NAME}"
SERVER_NAME="${NETBROKER_SERVER_NAME:-_}"
APP_UPSTREAM="${NETBROKER_APP_UPSTREAM:-127.0.0.1:8080}"
ENABLE_TLS="${NETBROKER_ENABLE_TLS:-false}"
ADMIN_EMAIL="${NETBROKER_TLS_EMAIL:-}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-nginx-ubuntu.sh" >&2
  exit 1
fi

set_env() {
  local key="$1"
  local value="$2"
  touch "${ENV_FILE}"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

apt-get update
apt-get install -y nginx

set_env "NETBROKER_HOST" "127.0.0.1"
set_env "NETBROKER_PORT" "${APP_UPSTREAM##*:}"
chmod 0600 "${ENV_FILE}"

cat > "${NGINX_SITE}" <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${SERVER_NAME};

    client_max_body_size 2m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    location / {
        proxy_pass http://${APP_UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 60s;
    }
}
NGINX

ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl restart "${APP_NAME}"
systemctl enable --now nginx
systemctl reload nginx

if command -v ufw >/dev/null 2>&1; then
  ufw allow 'Nginx Full' >/dev/null || true
fi

if [[ "${ENABLE_TLS}" =~ ^(1|true|yes|on)$ ]]; then
  if [[ "${SERVER_NAME}" == "_" || -z "${ADMIN_EMAIL}" ]]; then
    echo "Para TLS, defina NETBROKER_SERVER_NAME e NETBROKER_TLS_EMAIL." >&2
    exit 1
  fi
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx --non-interactive --agree-tos --redirect \
    --email "${ADMIN_EMAIL}" \
    -d "${SERVER_NAME}"
fi

echo "Nginx configurado para ${APP_NAME}."
echo "Aplicacao interna: http://${APP_UPSTREAM}"
echo "URL publica: http://${SERVER_NAME}/"
echo "Arquivo Nginx: ${NGINX_SITE}"
