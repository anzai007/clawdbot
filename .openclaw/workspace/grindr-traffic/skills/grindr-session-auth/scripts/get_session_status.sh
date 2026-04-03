#!/usr/bin/env bash
set -euo pipefail

ACTION="session.get_session_status"
ENDPOINT="http://127.0.0.1:8787/auth/session/status"

RESP="$(curl -sS -X POST "${ENDPOINT}" 2>/dev/null)" || {
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter"}}
JSON
  exit 0
}

printf '%s\n' "${RESP}"
