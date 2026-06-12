#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup-ldap-ubuntu.sh"

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

echo "NetBroker LDAP/Active Directory configuration"
echo

LDAP_URI="$(prompt_default "LDAP URI" "ldap://ad.example.local:389")"
LDAP_BASE_DN="$(prompt_default "Base DN" "DC=example,DC=local")"
LDAP_BIND_DN="$(prompt_default "Service bind DN" "CN=svc-netbroker,OU=Service Accounts,${LDAP_BASE_DN}")"
LDAP_BIND_PASSWORD="$(prompt_secret "Service bind password")"
LDAP_USER_FILTER="$(prompt_default "User filter" "(sAMAccountName={username})")"
LDAP_DEFAULT_ROLE="$(prompt_default "Default role" "readonly")"

echo
echo "Group DNs for RBAC mapping. Leave empty to skip a role."
LDAP_ADMIN_GROUP="$(prompt_default "Admin group DN" "CN=NetBroker Admins,OU=Groups,${LDAP_BASE_DN}")"
LDAP_NOC_GROUP="$(prompt_default "NOC group DN" "CN=NetBroker NOC,OU=Groups,${LDAP_BASE_DN}")"
LDAP_AUDITOR_GROUP="$(prompt_default "Auditor group DN" "CN=NetBroker Auditors,OU=Groups,${LDAP_BASE_DN}")"
LDAP_READONLY_GROUP="$(prompt_default "Readonly group DN" "CN=NetBroker Readonly,OU=Groups,${LDAP_BASE_DN}")"

GROUP_MAP=""
append_mapping() {
  local group_dn="$1"
  local role="$2"
  if [[ -n "${group_dn}" ]]; then
    if [[ -n "${GROUP_MAP}" ]]; then
      GROUP_MAP+=";"
    fi
    GROUP_MAP+="${group_dn}=${role}"
  fi
}

append_mapping "${LDAP_ADMIN_GROUP}" "admin"
append_mapping "${LDAP_NOC_GROUP}" "noc"
append_mapping "${LDAP_AUDITOR_GROUP}" "auditor"
append_mapping "${LDAP_READONLY_GROUP}" "readonly"

echo
echo "Applying LDAP configuration through ${SETUP_SCRIPT}"

sudo \
  NETBROKER_LDAP_URI="${LDAP_URI}" \
  NETBROKER_LDAP_BASE_DN="${LDAP_BASE_DN}" \
  NETBROKER_LDAP_BIND_DN="${LDAP_BIND_DN}" \
  NETBROKER_LDAP_BIND_PASSWORD="${LDAP_BIND_PASSWORD}" \
  NETBROKER_LDAP_USER_FILTER="${LDAP_USER_FILTER}" \
  NETBROKER_LDAP_DEFAULT_ROLE="${LDAP_DEFAULT_ROLE}" \
  NETBROKER_LDAP_GROUP_ROLE_MAP="${GROUP_MAP}" \
  bash "${SETUP_SCRIPT}"

