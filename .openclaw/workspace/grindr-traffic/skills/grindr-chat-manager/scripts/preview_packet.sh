#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_chat_manager_common.sh"

ACTION="chat.ws.request.preview"
BASE_URL="$(resolve_adapter_base_url)"
ENDPOINT="${BASE_URL}/chat/ws/request/preview"
PAYLOAD="${1:-}"

if [[ -z "${PAYLOAD}" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "MISSING_PAYLOAD" "缺少 JSON 参数"
  exit 0
fi

post_json "${ACTION}" "${ENDPOINT}" "${PAYLOAD}"
