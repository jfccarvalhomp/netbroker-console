#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup-ise-ubuntu.sh"

prompt_default() {
  local label="$1"
  local default_value="$2"
  local value
  read -r -p "${label} [${default_value}]: " value
  echo "${value:-${default_value}}"
}

echo "NetBroker Cisco ISE authorization configuration"
echo
echo "This enables ISE-style RBAC mapping after local, LDAP, or TACACS+ authentication."
echo

ISE_DEFAULT_ROLE="$(prompt_default "Default role" "readonly")"
ISE_USER_ROLE_MAP="$(prompt_default "User role map" "admin=admin;operador=noc;auditor=auditor")"
ISE_PROFILE_ROLE_MAP="$(prompt_default "ISE profile role map" "NetBroker-Admin=admin;NetBroker-NOC=noc;NetBroker-Auditor=auditor")"
ISE_SGT_ROLE_MAP="$(prompt_default "ISE SGT role map" "16=admin;17=noc;18=auditor;19=readonly")"

sudo \
  NETBROKER_ISE_DEFAULT_ROLE="${ISE_DEFAULT_ROLE}" \
  NETBROKER_ISE_USER_ROLE_MAP="${ISE_USER_ROLE_MAP}" \
  NETBROKER_ISE_PROFILE_ROLE_MAP="${ISE_PROFILE_ROLE_MAP}" \
  NETBROKER_ISE_SGT_ROLE_MAP="${ISE_SGT_ROLE_MAP}" \
  bash "${SETUP_SCRIPT}"
