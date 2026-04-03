#!/usr/bin/env bash
set -euo pipefail

ADAPTER_URL="http://127.0.0.1:8787/profile/me/get"

response=""
if ! response="$(curl -sS -X POST "${ADAPTER_URL}" -H "Content-Type: application/json" --data '{}' --max-time 20)"; then
  cat <<JSON
{"action":"get_me_profile","success":false,"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter: ${ADAPTER_URL}"}}
JSON
  exit 1
fi

printf '%s\n' "${response}"
