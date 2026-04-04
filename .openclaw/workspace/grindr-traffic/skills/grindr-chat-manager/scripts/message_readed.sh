#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONVERSATION_ID="${1:-}"
USER_ID="${2:-}"
MESSAGE_TIME="${3:-}"
REQUEST_ID="${4:-1}"

if [[ -z "${CONVERSATION_ID}" || -z "${USER_ID}" || -z "${MESSAGE_TIME}" ]]; then
  echo '{"action":"chat.ws.message_readed","success":false,"data":null,"meta":{},"error":{"code":"MISSING_ARGS","message":"参数不足：conversationId user messageTime"}}'
  exit 0
fi

PAYLOAD="$(python3 - "${REQUEST_ID}" "${CONVERSATION_ID}" "${USER_ID}" "${MESSAGE_TIME}" <<'PY'
import json
import sys
request_id = int(sys.argv[1])
conversation_id = sys.argv[2]
user_id = sys.argv[3]
message_time = sys.argv[4]
packet = {
    "requestId": request_id,
    "source": "",
    "type": "messageReaded",
    "data": [{"conversationId": conversation_id, "user": user_id, "messageTime": message_time}],
}
print(json.dumps(packet, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/send_packet.sh" "${PAYLOAD}"
