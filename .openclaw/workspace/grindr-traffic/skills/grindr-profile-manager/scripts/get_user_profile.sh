#!/usr/bin/env bash
set -euo pipefail

ADAPTER_URL="http://127.0.0.1:8787/profile/user/get"
PAYLOAD="${1:-}"

if [[ -z "${PAYLOAD}" ]]; then
  cat <<JSON
{"action":"get_user_profile","success":false,"error":{"code":"MISSING_PAYLOAD","message":"缺少参数：请传入 JSON，例如 '{\"profileId\":827555450}'"}}
JSON
  exit 1
fi

response=""
if ! response="$(curl -sS -X POST "${ADAPTER_URL}" -H "Content-Type: application/json" --data "${PAYLOAD}" --max-time 20)"; then
  cat <<JSON
{"action":"get_user_profile","success":false,"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter: ${ADAPTER_URL}"}}
JSON
  exit 1
fi

printf '%s\n' "${response}"
