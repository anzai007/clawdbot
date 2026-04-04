#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_chat_manager_common.sh"

ACTION="chat.ws.connection.connect"
BASE_URL="$(resolve_adapter_base_url)"
ENDPOINT="${BASE_URL}/chat/ws/connection/connect"
FORCE_RECONNECT="${1:-false}"

if [[ "${FORCE_RECONNECT}" != "true" && "${FORCE_RECONNECT}" != "false" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_FORCE_RECONNECT" "参数 forceReconnect 只能是 true/false"
  exit 0
fi

PAYLOAD="{\"forceReconnect\":${FORCE_RECONNECT}}"
post_json "${ACTION}" "${ENDPOINT}" "${PAYLOAD}"
