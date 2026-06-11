#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
DB_NAME="${NETBROKER_DB_NAME:-netbroker_console}"
DB_USER="${NETBROKER_DB_USER:-netbroker_console}"
DB_PASSWORD="${NETBROKER_DB_PASSWORD:-$(openssl rand -hex 24)}"
ENV_FILE="/etc/${APP_NAME}.env"
DROPIN_DIR="/etc/systemd/system/${APP_NAME}.service.d"
DROPIN_FILE="${DROPIN_DIR}/postgres.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-postgres-ubuntu.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y postgresql python3-psycopg2 openssl

run_psql() {
  (cd /tmp && sudo -u postgres psql "$@")
}

run_createdb() {
  (cd /tmp && sudo -u postgres createdb "$@")
}

if ! run_psql -tAc "select 1 from pg_roles where rolname='${DB_USER}'" | grep -q 1; then
  run_psql -v ON_ERROR_STOP=1 -c "create role ${DB_USER} login password '${DB_PASSWORD}'"
else
  run_psql -v ON_ERROR_STOP=1 -c "alter role ${DB_USER} with password '${DB_PASSWORD}'"
fi

if ! run_psql -tAc "select 1 from pg_database where datname='${DB_NAME}'" | grep -q 1; then
  run_createdb -O "${DB_USER}" "${DB_NAME}"
fi

cat > "${ENV_FILE}" <<ENV
NETBROKER_STORE=postgres
NETBROKER_POSTGRES_DSN=dbname=${DB_NAME} user=${DB_USER} password=${DB_PASSWORD} host=127.0.0.1 port=5432
ENV

chmod 0600 "${ENV_FILE}"
mkdir -p "${DROPIN_DIR}"
cat > "${DROPIN_FILE}" <<SERVICE
[Service]
EnvironmentFile=${ENV_FILE}
SERVICE

systemctl daemon-reload
systemctl restart "${APP_NAME}"

echo "PostgreSQL configurado para ${APP_NAME}."
echo "Banco: ${DB_NAME}"
echo "Usuario: ${DB_USER}"
echo "Arquivo de ambiente: ${ENV_FILE}"
