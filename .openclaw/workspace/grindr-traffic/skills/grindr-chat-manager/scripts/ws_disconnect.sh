#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_chat_manager_common.sh"

ACTION="chat.ws.connection.disconnect"
BASE_URL="$(resolve_adapter_base_url)"
ENDPOINT="${BASE_URL}/chat/ws/connection/disconnect"

post_json "${ACTION}" "${ENDPOINT}" '{}'
