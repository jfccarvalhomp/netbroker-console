#!/usr/bin/env bash
set -euo pipefail

APP_NAME="netbroker-console"
ENV_FILE="/etc/${APP_NAME}.env"
PROMETHEUS_FILE="/etc/prometheus/prometheus.yml"
METRICS_TOKEN="${NETBROKER_METRICS_TOKEN:-$(openssl rand -hex 24)}"
NETBROKER_TARGET="${NETBROKER_PROMETHEUS_TARGET:-127.0.0.1:8080}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute com sudo: sudo bash scripts/setup-observability-ubuntu.sh" >&2
  exit 1
fi

set_env() {
  local key="$1"
  local value="$2"
  touch "${ENV_FILE}"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

apt-get update
apt-get install -y prometheus openssl

set_env "NETBROKER_METRICS_TOKEN" "${METRICS_TOKEN}"
chmod 0600 "${ENV_FILE}"

if [[ -f "${PROMETHEUS_FILE}" ]]; then
  cp "${PROMETHEUS_FILE}" "${PROMETHEUS_FILE}.bak.$(date +%Y%m%d%H%M%S)"
else
  mkdir -p "$(dirname "${PROMETHEUS_FILE}")"
  cat > "${PROMETHEUS_FILE}" <<'PROM'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["127.0.0.1:9090"]
PROM
fi

sed -i '/# BEGIN NETBROKER CONSOLE/,/# END NETBROKER CONSOLE/d' "${PROMETHEUS_FILE}"
BLOCK_FILE="$(mktemp)"
TMP_FILE="$(mktemp)"
cat > "${BLOCK_FILE}" <<PROM
  # BEGIN NETBROKER CONSOLE
  - job_name: netbroker-console
    metrics_path: /metrics
    authorization:
      type: Bearer
      credentials: ${METRICS_TOKEN}
    static_configs:
      - targets: ["${NETBROKER_TARGET}"]
  # END NETBROKER CONSOLE
PROM

awk -v block_file="${BLOCK_FILE}" '
  /^scrape_configs:[[:space:]]*$/ {
    print
    while ((getline line < block_file) > 0) print line
    close(block_file)
    inserted = 1
    next
  }
  { print }
  END {
    if (!inserted) {
      print ""
      print "scrape_configs:"
      while ((getline line < block_file) > 0) print line
      close(block_file)
    }
  }
' "${PROMETHEUS_FILE}" > "${TMP_FILE}"
cat "${TMP_FILE}" > "${PROMETHEUS_FILE}"
rm -f "${BLOCK_FILE}" "${TMP_FILE}"

if command -v promtool >/dev/null 2>&1; then
  promtool check config "${PROMETHEUS_FILE}"
fi

systemctl restart "${APP_NAME}"
systemctl enable --now prometheus
systemctl restart prometheus

echo "Observabilidade externa configurada."
echo "Prometheus: http://$(hostname -I | awk '{print $1}'):9090/"
echo "Target NetBroker: ${NETBROKER_TARGET}"
echo "Token salvo em: ${ENV_FILE}"
echo "Teste: curl -H 'Authorization: Bearer ${METRICS_TOKEN}' http://127.0.0.1:8080/metrics"
