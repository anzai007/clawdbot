#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENDER="${1:-}"
TARGET="${2:-}"
TEXT="${3:-}"
REQUEST_ID="${4:-1}"
SOURCE="${5:-}"

if [[ -z "${SENDER}" || -z "${TARGET}" || -z "${TEXT}" ]]; then
  echo '{"action":"chat.ws.message_send_text","success":false,"data":null,"meta":{},"error":{"code":"MISSING_ARGS","message":"参数不足：sender target text"}}'
  exit 0
fi

PAYLOAD="$(python3 - "${REQUEST_ID}" "${SOURCE}" "${SENDER}" "${TARGET}" "${TEXT}" <<'PY'
import json
import sys
import uuid
from datetime import datetime, timezone

request_id = int(sys.argv[1])
source = sys.argv[2]
sender = sys.argv[3]
target = sys.argv[4]
text = sys.argv[5]

conversation_id = "-".join(sorted([sender, target]))
message = {
    "messageId": str(uuid.uuid4()),
    "conversationId": conversation_id,
    "sender": sender,
    "senderName": "",
    "senderAvatar": "",
    "senderTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "target": target,
    "messageType": "text",
    "messageContent": text,
    "isRead": False,
    "isRecalled": False,
    "isDeleted": False,
}
packet = {"requestId": request_id, "source": source, "type": "messageSend", "data": [message]}
print(json.dumps(packet, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/send_packet.sh" "${PAYLOAD}"
