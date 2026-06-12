#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
ENV_FILE="/etc/${APP_NAME}.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-tacacs-ubuntu.sh" >&2
  exit 1
fi

TACACS_HOST="${NETBROKER_TACACS_HOST:-}"
TACACS_SECRET="${NETBROKER_TACACS_SECRET:-}"
TACACS_PORT="${NETBROKER_TACACS_PORT:-49}"
TACACS_TIMEOUT="${NETBROKER_TACACS_TIMEOUT:-5}"
TACACS_DEFAULT_ROLE="${NETBROKER_TACACS_DEFAULT_ROLE:-readonly}"
TACACS_USER_ROLE_MAP="${NETBROKER_TACACS_USER_ROLE_MAP:-}"

if [[ -z "${TACACS_HOST}" || -z "${TACACS_SECRET}" ]]; then
  cat >&2 <<HELP
Defina NETBROKER_TACACS_HOST e NETBROKER_TACACS_SECRET antes de executar.

Exemplo:
sudo NETBROKER_TACACS_HOST="10.0.0.10" \\
  NETBROKER_TACACS_SECRET="shared-secret" \\
  NETBROKER_TACACS_DEFAULT_ROLE="readonly" \\
  NETBROKER_TACACS_USER_ROLE_MAP="admin=admin;operador=noc;auditor=auditor" \\
  bash scripts/setup-tacacs-ubuntu.sh
HELP
  exit 1
fi

apt-get update
apt-get install -y python3-pip
python3 -m pip install --break-system-packages tacacs_plus

touch "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

set_env "NETBROKER_AUTH_PROVIDER" "tacacs"
set_env "NETBROKER_TACACS_HOST" "${TACACS_HOST}"
set_env "NETBROKER_TACACS_SECRET" "${TACACS_SECRET}"
set_env "NETBROKER_TACACS_PORT" "${TACACS_PORT}"
set_env "NETBROKER_TACACS_TIMEOUT" "${TACACS_TIMEOUT}"
set_env "NETBROKER_TACACS_DEFAULT_ROLE" "${TACACS_DEFAULT_ROLE}"
set_env "NETBROKER_TACACS_USER_ROLE_MAP" "${TACACS_USER_ROLE_MAP}"

systemctl restart "${APP_NAME}"

echo "TACACS+ configurado para ${APP_NAME}."
echo "Host: ${TACACS_HOST}:${TACACS_PORT}"
echo "Default role: ${TACACS_DEFAULT_ROLE}"
