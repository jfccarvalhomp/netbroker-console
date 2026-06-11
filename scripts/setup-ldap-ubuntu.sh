#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
ENV_FILE="/etc/${APP_NAME}.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-ldap-ubuntu.sh" >&2
  exit 1
fi

LDAP_URI="${NETBROKER_LDAP_URI:-}"
LDAP_BASE_DN="${NETBROKER_LDAP_BASE_DN:-}"
LDAP_BIND_DN="${NETBROKER_LDAP_BIND_DN:-}"
LDAP_BIND_PASSWORD="${NETBROKER_LDAP_BIND_PASSWORD:-}"
LDAP_USER_FILTER="${NETBROKER_LDAP_USER_FILTER:-(sAMAccountName={username})}"
LDAP_DEFAULT_ROLE="${NETBROKER_LDAP_DEFAULT_ROLE:-readonly}"
LDAP_GROUP_ROLE_MAP="${NETBROKER_LDAP_GROUP_ROLE_MAP:-}"

if [[ -z "${LDAP_URI}" || -z "${LDAP_BASE_DN}" ]]; then
  cat >&2 <<HELP
Defina ao menos NETBROKER_LDAP_URI e NETBROKER_LDAP_BASE_DN antes de executar.

Exemplo:
sudo NETBROKER_LDAP_URI="ldap://ad.example.local:389" \\
  NETBROKER_LDAP_BASE_DN="DC=example,DC=local" \\
  NETBROKER_LDAP_BIND_DN="CN=svc-netbroker,OU=Service Accounts,DC=example,DC=local" \\
  NETBROKER_LDAP_BIND_PASSWORD="senha" \\
  NETBROKER_LDAP_GROUP_ROLE_MAP="CN=NetBroker Admins,OU=Groups,DC=example,DC=local=admin;CN=NetBroker NOC,OU=Groups,DC=example,DC=local=noc" \\
  bash scripts/setup-ldap-ubuntu.sh
HELP
  exit 1
fi

apt-get update
apt-get install -y python3-ldap

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

set_env "NETBROKER_AUTH_PROVIDER" "ldap"
set_env "NETBROKER_LDAP_URI" "${LDAP_URI}"
set_env "NETBROKER_LDAP_BASE_DN" "${LDAP_BASE_DN}"
set_env "NETBROKER_LDAP_BIND_DN" "${LDAP_BIND_DN}"
set_env "NETBROKER_LDAP_BIND_PASSWORD" "${LDAP_BIND_PASSWORD}"
set_env "NETBROKER_LDAP_USER_FILTER" "${LDAP_USER_FILTER}"
set_env "NETBROKER_LDAP_DEFAULT_ROLE" "${LDAP_DEFAULT_ROLE}"
set_env "NETBROKER_LDAP_GROUP_ROLE_MAP" "${LDAP_GROUP_ROLE_MAP}"

systemctl restart "${APP_NAME}"

echo "LDAP configurado para ${APP_NAME}."
echo "Provider: ldap"
echo "Base DN: ${LDAP_BASE_DN}"
