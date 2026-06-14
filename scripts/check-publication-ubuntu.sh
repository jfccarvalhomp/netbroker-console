#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${NETBROKER_SERVER_NAME:-}}"
APP_URL="${NETBROKER_LOCAL_URL:-http://127.0.0.1:8080}"
PUBLIC_IP_URL="${NETBROKER_PUBLIC_IP_URL:-https://ifconfig.me}"

ok() {
  echo "[OK] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

fail() {
  echo "[FAIL] $*" >&2
}

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "Comando disponivel: $1"
    return 0
  fi
  warn "Comando ausente: $1"
  return 1
}

http_code() {
  local url="$1"
  curl -k -L -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 12 "$url" || true
}

echo "NetBroker publication check"
echo

check_command curl || true
check_command systemctl || true

if systemctl is-active --quiet netbroker-console; then
  ok "Servico netbroker-console ativo"
else
  fail "Servico netbroker-console nao esta ativo"
  systemctl --no-pager --full status netbroker-console || true
fi

if command -v nginx >/dev/null 2>&1; then
  ok "Nginx instalado"
  if nginx -t >/dev/null 2>&1; then
    ok "Configuracao do Nginx valida"
  else
    fail "Configuracao do Nginx invalida"
    nginx -t || true
  fi
else
  warn "Nginx nao instalado"
fi

local_health="$(http_code "${APP_URL}/api/health")"
if [[ "${local_health}" == "200" ]]; then
  ok "Backend local respondeu ${APP_URL}/api/health"
else
  fail "Backend local retornou HTTP ${local_health} em ${APP_URL}/api/health"
fi

if [[ -z "${DOMAIN}" ]]; then
  warn "Dominio nao informado. Use: bash scripts/check-publication-ubuntu.sh exemplo.com.br"
  exit 0
fi

echo
echo "Dominio: ${DOMAIN}"

public_ip="$(curl -4 -sS --connect-timeout 5 --max-time 10 "${PUBLIC_IP_URL}" || true)"
if [[ -n "${public_ip}" ]]; then
  ok "IP publico detectado: ${public_ip}"
else
  warn "Nao foi possivel detectar IP publico via ${PUBLIC_IP_URL}"
fi

dns_values=""
if command -v dig >/dev/null 2>&1; then
  dns_values="$(dig +short A "${DOMAIN}" | grep -E '^[0-9.]+$' || true)"
elif command -v getent >/dev/null 2>&1; then
  dns_values="$(getent ahostsv4 "${DOMAIN}" | awk '{print $1}' | sort -u || true)"
else
  warn "Instale dnsutils para diagnostico DNS mais completo: sudo apt-get install -y dnsutils"
fi

if [[ -n "${dns_values}" ]]; then
  ok "DNS A encontrado para ${DOMAIN}: $(echo "${dns_values}" | paste -sd ', ' -)"
  if [[ -n "${public_ip}" ]] && echo "${dns_values}" | grep -qx "${public_ip}"; then
    ok "DNS aponta para o IP publico deste servidor"
  elif [[ -n "${public_ip}" ]]; then
    fail "DNS nao aponta para ${public_ip}. Ajuste o registro A antes de tentar Certbot."
  fi
else
  fail "Nenhum registro A encontrado para ${DOMAIN}"
fi

http_public="$(http_code "http://${DOMAIN}/api/health")"
if [[ "${http_public}" == "200" ]]; then
  ok "HTTP publico respondeu http://${DOMAIN}/api/health"
else
  warn "HTTP publico retornou ${http_public} em http://${DOMAIN}/api/health"
fi

https_public="$(http_code "https://${DOMAIN}/api/health")"
if [[ "${https_public}" == "200" ]]; then
  ok "HTTPS publico respondeu https://${DOMAIN}/api/health"
else
  warn "HTTPS ainda nao respondeu 200 para ${DOMAIN}; esperado antes de emitir TLS"
fi

echo
echo "Se DNS e HTTP publico estiverem OK, rode:"
echo "sudo NETBROKER_SERVER_NAME=\"${DOMAIN}\" NETBROKER_ENABLE_TLS=\"true\" NETBROKER_TLS_EMAIL=\"seu-email@dominio.com.br\" bash scripts/setup-nginx-ubuntu.sh"
