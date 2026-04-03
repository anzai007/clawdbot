#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-8787}"

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTER_DIR="${WORKSPACE_DIR}/adapters/grindr_adapter"
ENV_FILE="${WORKSPACE_DIR}/.secrets/grindr.env"
REQ_FILE="${ADAPTER_DIR}/requirements.txt"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 未找到 python3，请先安装 Python 3。"
  exit 1
fi

if ! python3 - <<'PY' >/dev/null 2>&1
import flask, requests
print('ok')
PY
then
  echo "[ERROR] 缺少 adapter 依赖（flask/requests）。"
  echo "请执行：python3 -m pip install -r ${REQ_FILE}"
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] 缺少环境文件：${ENV_FILE}"
  echo "请先执行：cp ${WORKSPACE_DIR}/.secrets/grindr.env.example ${ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

cd "${ADAPTER_DIR}"
ADAPTER_HOST="${HOST}" ADAPTER_PORT="${PORT}" python3 app.py
