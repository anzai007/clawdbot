#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_ID="${1:-}"
MESSAGE_ID="${2:-}"
REQUEST_ID="${3:-1}"

if [[ -z "${USER_ID}" || -z "${MESSAGE_ID}" ]]; then
  echo '{"action":"chat.ws.message_recall","success":false,"data":null,"meta":{},"error":{"code":"MISSING_ARGS","message":"参数不足：user messageId"}}'
  exit 0
fi

PAYLOAD="$(python3 - "${REQUEST_ID}" "${USER_ID}" "${MESSAGE_ID}" <<'PY'
import json
import sys
request_id = int(sys.argv[1])
user_id = sys.argv[2]
message_id = sys.argv[3]
packet = {"requestId": request_id, "source": "", "type": "messageRecall", "data": [{"user": user_id, "messageId": message_id}]}
print(json.dumps(packet, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/ws_send_and_pull.sh" "${PAYLOAD}" "20" "true" "false"
