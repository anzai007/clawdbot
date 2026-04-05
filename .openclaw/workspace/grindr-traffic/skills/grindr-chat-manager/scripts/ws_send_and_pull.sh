#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_chat_manager_common.sh"

ACTION="chat.ws.send_and_pull"
BASE_URL="$(resolve_adapter_base_url)"
ENDPOINT="${BASE_URL}/chat/ws/request/send"
PAYLOAD="${1:-}"
PULL_LIMIT="${2:-20}"
CLEAR_NOTIFY="${3:-true}"
FORCE_RECONNECT="${4:-false}"

if [[ -z "${PAYLOAD}" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "MISSING_PAYLOAD" "缺少 JSON 参数"
  exit 0
fi

if ! [[ "${PULL_LIMIT}" =~ ^[0-9]+$ ]] || [[ "${PULL_LIMIT}" -le 0 ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_LIMIT" "参数 pullLimit 必须是大于 0 的整数"
  exit 0
fi

if [[ "${CLEAR_NOTIFY}" != "true" && "${CLEAR_NOTIFY}" != "false" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_CLEAR" "参数 clear 只能是 true/false"
  exit 0
fi

if [[ "${FORCE_RECONNECT}" != "true" && "${FORCE_RECONNECT}" != "false" ]]; then
  json_error "${ACTION}" "${ENDPOINT}" "INVALID_FORCE_RECONNECT" "参数 forceReconnect 只能是 true/false"
  exit 0
fi

# 兼容两种输入：
# 1) 底层协议包：包含 requestId/type/data
# 2) 业务简化包：包含 senderProfileId/targetProfileId/message
NORMALIZED="$(python3 - "${PAYLOAD}" <<'PY'
import json
import sys
import time
import uuid
from datetime import datetime, timezone

raw = sys.argv[1]

try:
    obj = json.loads(raw)
except json.JSONDecodeError:
    print(json.dumps({"ok": False, "code": "INVALID_JSON", "message": "payload 不是合法 JSON"}, ensure_ascii=False))
    raise SystemExit(0)

if not isinstance(obj, dict):
    print(json.dumps({"ok": False, "code": "INVALID_PAYLOAD", "message": "payload 必须是 JSON 对象"}, ensure_ascii=False))
    raise SystemExit(0)

if "requestId" in obj and "type" in obj and "data" in obj:
    request_id = obj.get("requestId")
    if not isinstance(request_id, int) or request_id <= 0:
        print(json.dumps({"ok": False, "code": "INVALID_REQUEST_ID", "message": "requestId 必须是大于 0 的整数"}, ensure_ascii=False))
        raise SystemExit(0)
    print(json.dumps({"ok": True, "packet": obj}, ensure_ascii=False))
    raise SystemExit(0)

sender = str(obj.get("senderProfileId", "")).strip()
target = str(obj.get("targetProfileId", "")).strip()
message = str(obj.get("message", "")).strip()

if not sender or not target or not message:
    print(
        json.dumps(
            {
                "ok": False,
                "code": "INVALID_PAYLOAD_SHAPE",
                "message": "payload 需包含 senderProfileId、targetProfileId、message，或直接传入协议包",
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0)

conversation_id = "-".join(sorted([sender, target]))
request_id = int(time.time() * 1000)

packet = {
    "requestId": request_id,
    "source": str(obj.get("source", "")),
    "type": "messageSend",
    "data": [
        {
            "messageId": str(uuid.uuid4()),
            "conversationId": conversation_id,
            "sender": sender,
            "senderName": "",
            "senderAvatar": "",
            "senderTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "target": target,
            "messageType": "text",
            "messageContent": message,
            "isRead": False,
            "isRecalled": False,
            "isDeleted": False,
        }
    ],
}

print(json.dumps({"ok": True, "packet": packet}, ensure_ascii=False))
PY
)"

NORMALIZED_OK="$(python3 - "${NORMALIZED}" <<'PY'
import json
import sys

try:
    obj = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("false")
    raise SystemExit(0)

print("true" if obj.get("ok") is True else "false")
PY
)"

if [[ "${NORMALIZED_OK}" != "true" ]]; then
  CODE="$(python3 - "${NORMALIZED}" <<'PY'
import json
import sys

try:
    obj = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("INVALID_PAYLOAD")
    raise SystemExit(0)
print(obj.get("code", "INVALID_PAYLOAD"))
PY
)"
  MSG="$(python3 - "${NORMALIZED}" <<'PY'
import json
import sys

try:
    obj = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("payload 标准化失败")
    raise SystemExit(0)
print(obj.get("message", "payload 标准化失败"))
PY
)"
  json_error "${ACTION}" "${ENDPOINT}" "${CODE}" "${MSG}"
  exit 0
fi

NORMALIZED_PAYLOAD="$(python3 - "${NORMALIZED}" <<'PY'
import json
import sys

obj = json.loads(sys.argv[1])
print(json.dumps(obj["packet"], ensure_ascii=False))
PY
)"

# 第一步：确保 WS 长连接可用。
CONNECT_JSON="$(bash "${SCRIPT_DIR}/ws_connect.sh" "${FORCE_RECONNECT}")"
# 第二步：发送前先清空旧通知，避免把历史消息误判成本次发送结果。
PRE_PULL_JSON="$(bash "${SCRIPT_DIR}/ws_pull_notify.sh" "200" "true")"
# 第三步：发送协议包（adapter 内会做结构校验）。
SEND_JSON="$(bash "${SCRIPT_DIR}/send_packet.sh" "${NORMALIZED_PAYLOAD}")"
# 第四步：立即拉取通知缓冲，拿到本次发送后的反馈。
PULL_JSON="$(bash "${SCRIPT_DIR}/ws_pull_notify.sh" "${PULL_LIMIT}" "${CLEAR_NOTIFY}")"

python3 - "${CONNECT_JSON}" "${PRE_PULL_JSON}" "${SEND_JSON}" "${PULL_JSON}" "${NORMALIZED_PAYLOAD}" <<'PY'
import json
import sys
from typing import Any


def parse_json(raw: str, fallback_action: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "action": fallback_action,
            "success": False,
            "data": None,
            "meta": {},
            "error": {
                "code": "INVALID_JSON",
                "message": "子步骤返回了无法解析的 JSON",
            },
        }

    if not isinstance(value, dict):
        return {
            "action": fallback_action,
            "success": False,
            "data": None,
            "meta": {},
            "error": {
                "code": "INVALID_JSON_TYPE",
                "message": "子步骤返回结果不是 JSON 对象",
            },
        }
    return value


connect = parse_json(sys.argv[1], "chat.ws.connection.connect")
pre_pull = parse_json(sys.argv[2], "chat.ws.notify.pull")
send = parse_json(sys.argv[3], "chat.ws.request.send")
pull = parse_json(sys.argv[4], "chat.ws.notify.pull")
normalized_packet = parse_json(sys.argv[5], "chat.ws.request.send")

connect_ok = bool(connect.get("success"))
send_ok = bool(send.get("success"))
pull_ok = bool(pull.get("success"))
executed = bool((send.get("data") or {}).get("executed"))

success = connect_ok and send_ok and pull_ok and executed
error = None
if not success:
    error = {
        "code": "CHAIN_FAILED",
        "message": "ws_connect/send/pull 链路未全部成功，请查看 steps 字段",
    }

result = {
    "action": "chat.ws.send_and_pull",
    "success": success,
    "data": {
        "executed": executed,
        "normalizedPacket": normalized_packet,
        "steps": {
            "connect": connect,
            "prePull": pre_pull,
            "send": send,
            "pull": pull,
        },
    },
    "meta": {
        "flow": ["connect", "prePull", "send", "pull"],
    },
    "error": error,
}
print(json.dumps(result, ensure_ascii=False))
PY
