#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_chat_manager_common.sh"

ACTION="chat.ws.notify.pull"
BASE_URL="$(resolve_adapter_base_url)"
ENDPOINT="${BASE_URL}/chat/ws/notify/pull"
LIMIT="${1:-20}"
CLEAR="${2:-true}"

if ! [[ "${LIMIT}" =~ ^[0-9]+$ ]] || [[ "${LIMIT}" -le 0 ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_LIMIT" "参数 limit 必须是大于 0 的整数"
  exit 0
fi

if [[ "${CLEAR}" != "true" && "${CLEAR}" != "false" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_CLEAR" "参数 clear 只能是 true/false"
  exit 0
fi

PAYLOAD="{\"limit\":${LIMIT},\"clear\":${CLEAR}}"
post_json "${ACTION}" "${ENDPOINT}" "${PAYLOAD}"
