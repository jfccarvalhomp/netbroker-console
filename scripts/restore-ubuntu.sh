#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
APP_DIR="/opt/${APP_NAME}"
ENV_FILE="/etc/${APP_NAME}.env"
ARCHIVE="${1:-}"
WORK_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/restore-ubuntu.sh /var/backups/netbroker-console/arquivo.tar.gz" >&2
  exit 1
fi

if [[ -z "${ARCHIVE}" || ! -f "${ARCHIVE}" ]]; then
  echo "Informe um arquivo de backup valido." >&2
  echo "Uso: sudo bash scripts/restore-ubuntu.sh /var/backups/netbroker-console/netbroker-console-YYYYMMDD-HHMMSS.tar.gz" >&2
  exit 1
fi

tar -xzf "${ARCHIVE}" -C "${WORK_DIR}"

if [[ ! -f "${WORK_DIR}/manifest.txt" ]]; then
  echo "Backup invalido: manifest.txt nao encontrado." >&2
  exit 1
fi

echo "Manifesto do backup:"
cat "${WORK_DIR}/manifest.txt"
echo

systemctl stop "${APP_NAME}" 2>/dev/null || true

if [[ -f "${WORK_DIR}/files/etc/${APP_NAME}.env" ]]; then
  cp -a "${WORK_DIR}/files/etc/${APP_NAME}.env" "${ENV_FILE}"
  chmod 0600 "${ENV_FILE}"
fi

if [[ -d "${WORK_DIR}/files/opt/${APP_NAME}/data" ]]; then
  mkdir -p "${APP_DIR}"
  rm -rf "${APP_DIR}/data"
  cp -a "${WORK_DIR}/files/opt/${APP_NAME}/data" "${APP_DIR}/data"
  if id "${APP_NAME}" >/dev/null 2>&1; then
    chown -R "${APP_NAME}:${APP_NAME}" "${APP_DIR}/data"
  fi
fi

if [[ -f "${WORK_DIR}/files/etc/nginx/sites-available/${APP_NAME}" ]]; then
  mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
  cp -a "${WORK_DIR}/files/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-available/${APP_NAME}"
  ln -sfn "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"
fi

if [[ -f "${WORK_DIR}/files/etc/prometheus/prometheus.yml" ]]; then
  mkdir -p /etc/prometheus
  cp -a "${WORK_DIR}/files/etc/prometheus/prometheus.yml" /etc/prometheus/prometheus.yml
fi

STORE="json"
POSTGRES_DSN=""
if [[ -f "${ENV_FILE}" ]]; then
  STORE="$(grep -E '^NETBROKER_STORE=' "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true)"
  POSTGRES_DSN="$(grep -E '^NETBROKER_POSTGRES_DSN=' "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true)"
fi

if [[ -f "${WORK_DIR}/postgres/netbroker-console.dump" ]]; then
  if [[ "${STORE}" != "postgres" || -z "${POSTGRES_DSN}" ]]; then
    echo "Backup contem dump PostgreSQL, mas NETBROKER_POSTGRES_DSN nao esta configurado." >&2
    exit 1
  fi
  if ! command -v pg_restore >/dev/null 2>&1; then
    echo "pg_restore nao encontrado. Instale postgresql-client." >&2
    exit 1
  fi
  pg_restore --clean --if-exists --no-owner --no-privileges --dbname="${POSTGRES_DSN}" "${WORK_DIR}/postgres/netbroker-console.dump"
fi

systemctl daemon-reload
systemctl start "${APP_NAME}"

if command -v nginx >/dev/null 2>&1; then
  nginx -t
  systemctl reload nginx || true
fi

if systemctl list-unit-files prometheus.service >/dev/null 2>&1; then
  systemctl restart prometheus || true
fi

echo "Restore concluido."
echo "Valide com: sudo systemctl status ${APP_NAME}"
