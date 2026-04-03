#!/usr/bin/env bash
set -euo pipefail

# 读取指定用户资料：必须传入 profileId JSON。
ACTION="discovery.get_user_profile"
ENDPOINT="http://127.0.0.1:8787/discovery/user/get"
PAYLOAD="${1:-}"

if [[ -z "${PAYLOAD}" ]]; then
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"MISSING_PAYLOAD","message":"缺少 JSON 参数，例如 '{\"profileId\":827555450}'"}}
JSON
  exit 0
fi

RESP="$(curl -sS -X POST "${ENDPOINT}" -H 'Content-Type: application/json' -d "${PAYLOAD}" --max-time 20 2>/dev/null)" || {
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter"}}
JSON
  exit 0
}

printf '%s\n' "${RESP}"
