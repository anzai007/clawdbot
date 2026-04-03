#!/usr/bin/env bash
set -euo pipefail

# 输入参数占位：host 与 port 可选
HOST="${1:-127.0.0.1}"
PORT="${2:-18081}"

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTER_DIR="${WORKSPACE_DIR}/adapters/grindr_adapter"
ENV_FILE="${WORKSPACE_DIR}/.secrets/grindr.env"

# 如果存在本地环境文件，则自动加载
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

# 启动骨架服务（仅占位路由）
cd "${ADAPTER_DIR}"
python3 -m uvicorn app:app --host "${HOST}" --port "${PORT}"
