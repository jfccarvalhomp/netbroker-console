#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup-tacacs-ubuntu.sh"

prompt_default() {
  local label="$1"
  local default_value="$2"
  local value
  read -r -p "${label} [${default_value}]: " value
  echo "${value:-${default_value}}"
}

prompt_secret() {
  local label="$1"
  local value
  read -r -s -p "${label}: " value
  echo
  echo "${value}"
}

echo "NetBroker TACACS+ configuration"
echo

TACACS_HOST="$(prompt_default "TACACS+ host" "10.0.0.10")"
TACACS_PORT="$(prompt_default "TACACS+ port" "49")"
TACACS_SECRET="$(prompt_secret "TACACS+ shared secret")"
TACACS_TIMEOUT="$(prompt_default "Timeout seconds" "5")"
TACACS_DEFAULT_ROLE="$(prompt_default "Default role" "readonly")"
TACACS_USER_ROLE_MAP="$(prompt_default "User role map" "admin=admin;operador=noc;auditor=auditor")"

sudo \
  NETBROKER_TACACS_HOST="${TACACS_HOST}" \
  NETBROKER_TACACS_SECRET="${TACACS_SECRET}" \
  NETBROKER_TACACS_PORT="${TACACS_PORT}" \
  NETBROKER_TACACS_TIMEOUT="${TACACS_TIMEOUT}" \
  NETBROKER_TACACS_DEFAULT_ROLE="${TACACS_DEFAULT_ROLE}" \
  NETBROKER_TACACS_USER_ROLE_MAP="${TACACS_USER_ROLE_MAP}" \
  bash "${SETUP_SCRIPT}"
