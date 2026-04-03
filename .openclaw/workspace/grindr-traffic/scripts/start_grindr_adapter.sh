#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-8787}"

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTER_DIR="${WORKSPACE_DIR}/adapters/grindr_adapter"
ENV_FILE="${WORKSPACE_DIR}/.secrets/grindr.env"
REQ_FILE="${ADAPTER_DIR}/requirements.txt"

if [[ ! -d "${ADAPTER_DIR}" ]]; then
  echo "[ERROR] adapter 目录不存在：${ADAPTER_DIR}"
  exit 1
fi

if [[ ! -f "${REQ_FILE}" ]]; then
  echo "[ERROR] requirements 文件不存在：${REQ_FILE}"
  exit 1
fi

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

# 会话文件缺失时自动从示例创建，避免 session-auth 骨架路由首次启动失败。
SESSION_FILE_VALUE="${GRINDR_SESSION_FILE:-./.secrets/grindr.session.json}"
if [[ "${SESSION_FILE_VALUE}" = /* ]]; then
  SESSION_FILE_PATH="${SESSION_FILE_VALUE}"
else
  SESSION_FILE_PATH="${WORKSPACE_DIR}/${SESSION_FILE_VALUE#./}"
fi

if [[ ! -f "${SESSION_FILE_PATH}" ]]; then
  mkdir -p "$(dirname "${SESSION_FILE_PATH}")"
  if [[ -f "${WORKSPACE_DIR}/.secrets/grindr.session.json.example" ]]; then
    cp "${WORKSPACE_DIR}/.secrets/grindr.session.json.example" "${SESSION_FILE_PATH}"
  else
    printf '{\"authToken\":\"replace_me\",\"sessionToken\":\"replace_me\",\"thirdPartyUserId\":\"replace_me\",\"thirdPartyVendor\":\"apple\",\"updatedAt\":\"replace_me\",\"source\":\"bootstrap\"}\\n' > "${SESSION_FILE_PATH}"
  fi
fi

cd "${ADAPTER_DIR}"
echo "[INFO] 启动 grindr_adapter: http://${HOST}:${PORT}"
ADAPTER_HOST="${HOST}" ADAPTER_PORT="${PORT}" python3 app.py
