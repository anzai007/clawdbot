#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUEST_ID="${1:-1}"

PAYLOAD="$(python3 - "${REQUEST_ID}" <<'PY'
import json
import sys
request_id = int(sys.argv[1])
print(json.dumps({"requestId": request_id, "source": "", "type": "userList", "data": []}, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/send_packet.sh" "${PAYLOAD}"
