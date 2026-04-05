#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENDER="${1:-}"
TARGET="${2:-}"
CREATED_AT="${3:-}"
MEDIA_ID="${4:-}"
EXPIRING="${5:-}"
TAKEN_ON_GRINDR="${6:-}"
REQUEST_ID="${7:-1}"

if [[ -z "${SENDER}" || -z "${TARGET}" || -z "${CREATED_AT}" || -z "${MEDIA_ID}" || -z "${EXPIRING}" || -z "${TAKEN_ON_GRINDR}" ]]; then
  echo '{"action":"chat.ws.send_media","success":false,"data":null,"meta":{},"error":{"code":"MISSING_ARGS","message":"参数不足：sender target createdAt mediaId expiring takenOnGrindr"}}'
  exit 0
fi

PAYLOAD="$(python3 - "${REQUEST_ID}" "${SENDER}" "${TARGET}" "${CREATED_AT}" "${MEDIA_ID}" "${EXPIRING}" "${TAKEN_ON_GRINDR}" <<'PY'
import json
import sys

request_id = int(sys.argv[1])
sender = sys.argv[2]
target = sys.argv[3]
created_at = int(sys.argv[4])
media_id = int(sys.argv[5])
expiring = sys.argv[6].lower() == "true"
taken_on_grindr = sys.argv[7].lower() == "true"

packet = {
    "requestId": request_id,
    "source": "",
    "type": "grindrChatSendMedia",
    "data": [
        {
            "sender": sender,
            "target": target,
            "createdAt": created_at,
            "expiring": expiring,
            "mediaId": media_id,
            "takenOnGrindr": taken_on_grindr,
        }
    ],
}
print(json.dumps(packet, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/ws_send_and_pull.sh" "${PAYLOAD}" "20" "true" "false"
