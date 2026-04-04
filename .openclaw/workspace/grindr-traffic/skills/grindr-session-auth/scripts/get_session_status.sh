#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ADAPTER_BASE_URL="$("${WORKSPACE_DIR}/scripts/resolve_grindr_adapter_base_url.sh")"


ACTION="session.get_session_status"
ENDPOINT="${ADAPTER_BASE_URL}/auth/session/status"

RESP="$(curl -sS -X POST "${ENDPOINT}" 2>/dev/null)" || {
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter"}}
JSON
  exit 0
}

printf '%s\n' "${RESP}"
