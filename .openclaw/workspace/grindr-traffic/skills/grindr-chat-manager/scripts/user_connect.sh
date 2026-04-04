#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_ID="${1:-}"
REQUEST_ID="${2:-1}"

if [[ -z "${USER_ID}" ]]; then
  echo '{"action":"chat.ws.user_connect","success":false,"data":null,"meta":{},"error":{"code":"MISSING_USER","message":"缺少 user 参数"}}'
  exit 0
fi

PAYLOAD="$(python3 - "${REQUEST_ID}" "${USER_ID}" <<'PY'
import json
import sys
request_id = int(sys.argv[1])
user_id = sys.argv[2]
print(json.dumps({"requestId": request_id, "source": "", "type": "userConnect", "data": [{"user": user_id}]}, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/send_packet.sh" "${PAYLOAD}"
