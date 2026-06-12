#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
ENV_FILE="/etc/${APP_NAME}.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-ise-ubuntu.sh" >&2
  exit 1
fi

ISE_DEFAULT_ROLE="${NETBROKER_ISE_DEFAULT_ROLE:-readonly}"
ISE_USER_ROLE_MAP="${NETBROKER_ISE_USER_ROLE_MAP:-}"
ISE_PROFILE_ROLE_MAP="${NETBROKER_ISE_PROFILE_ROLE_MAP:-}"
ISE_SGT_ROLE_MAP="${NETBROKER_ISE_SGT_ROLE_MAP:-}"

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

set_env "NETBROKER_ISE_ENABLED" "true"
set_env "NETBROKER_ISE_DEFAULT_ROLE" "${ISE_DEFAULT_ROLE}"
set_env "NETBROKER_ISE_USER_ROLE_MAP" "${ISE_USER_ROLE_MAP}"
set_env "NETBROKER_ISE_PROFILE_ROLE_MAP" "${ISE_PROFILE_ROLE_MAP}"
set_env "NETBROKER_ISE_SGT_ROLE_MAP" "${ISE_SGT_ROLE_MAP}"

systemctl restart "${APP_NAME}"

echo "Cisco ISE authorization policy enabled for ${APP_NAME}."
echo "Default role: ${ISE_DEFAULT_ROLE}"
