#!/usr/bin/env bash
set -euo pipefail

# 读取附近用户列表：允许不传参数，默认空对象。
ACTION="discovery.get_nearby_profiles"
ENDPOINT="http://127.0.0.1:8787/discovery/nearby/get"
PAYLOAD="${1:-{}}"

if [[ -z "${PAYLOAD}" ]]; then
  PAYLOAD='{}'
fi

RESP="$(curl -sS -X POST "${ENDPOINT}" -H 'Content-Type: application/json' -d "${PAYLOAD}" --max-time 20 2>/dev/null)" || {
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter"}}
JSON
  exit 0
}

printf '%s\n' "${RESP}"
