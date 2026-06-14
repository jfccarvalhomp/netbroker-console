#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
APP_DIR="/opt/${APP_NAME}"
ENV_FILE="/etc/${APP_NAME}.env"
BACKUP_DIR="${NETBROKER_BACKUP_DIR:-/var/backups/${APP_NAME}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
WORK_DIR="$(mktemp -d)"
ARCHIVE="${BACKUP_DIR}/${APP_NAME}-${STAMP}.tar.gz"

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/backup-ubuntu.sh" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}" "${WORK_DIR}/files" "${WORK_DIR}/postgres"
chmod 0700 "${BACKUP_DIR}"

copy_if_exists() {
  local source="$1"
  local target="$2"
  if [[ -e "${source}" ]]; then
    mkdir -p "$(dirname "${target}")"
    cp -a "${source}" "${target}"
  fi
}

copy_if_exists "${ENV_FILE}" "${WORK_DIR}/files/etc/${APP_NAME}.env"
copy_if_exists "/etc/nginx/sites-available/${APP_NAME}" "${WORK_DIR}/files/etc/nginx/sites-available/${APP_NAME}"
copy_if_exists "/etc/prometheus/prometheus.yml" "${WORK_DIR}/files/etc/prometheus/prometheus.yml"

if [[ -d "${APP_DIR}/data" ]]; then
  mkdir -p "${WORK_DIR}/files/opt/${APP_NAME}"
  cp -a "${APP_DIR}/data" "${WORK_DIR}/files/opt/${APP_NAME}/data"
fi

STORE="json"
POSTGRES_DSN=""
if [[ -f "${ENV_FILE}" ]]; then
  STORE="$(grep -E '^NETBROKER_STORE=' "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true)"
  POSTGRES_DSN="$(grep -E '^NETBROKER_POSTGRES_DSN=' "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true)"
fi

cat > "${WORK_DIR}/manifest.txt" <<MANIFEST
app=${APP_NAME}
created_at=${STAMP}
host=$(hostname -f 2>/dev/null || hostname)
store=${STORE:-json}
MANIFEST

if [[ "${STORE}" == "postgres" && -n "${POSTGRES_DSN}" ]]; then
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump nao encontrado. Instale postgresql-client ou rode setup-postgres-ubuntu.sh." >&2
    exit 1
  fi
  pg_dump "${POSTGRES_DSN}" --format=custom --file="${WORK_DIR}/postgres/netbroker-console.dump"
fi

tar -C "${WORK_DIR}" -czf "${ARCHIVE}" .
chmod 0600 "${ARCHIVE}"

echo "Backup criado com sucesso:"
echo "${ARCHIVE}"
