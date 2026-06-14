#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="${BASH_SOURCE[0]%/*}"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python nao encontrado. Instale python3 ou defina PYTHON_BIN." >&2
    exit 1
  fi
fi

"${PYTHON_BIN}" -m compileall -q server.py worker.py netbroker_console

shopt -s globstar nullglob
BASH_BIN="${BASH:-bash}"
for script in scripts/**/*.sh scripts/*.sh; do
  "${BASH_BIN}" -n "${script}"
done

"${PYTHON_BIN}" -m json.tool monitoring/grafana-netbroker-dashboard.json >/dev/null

test -f index.html
test -f styles.css
test -f app.js
test -d assets

echo "Validacao local concluida com sucesso."
