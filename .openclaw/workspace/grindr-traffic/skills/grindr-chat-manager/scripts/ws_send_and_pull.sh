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

# 第一步：确保 WS 长连接可用。
CONNECT_JSON="$(bash "${SCRIPT_DIR}/ws_connect.sh" "${FORCE_RECONNECT}")"
# 第二步：发送协议包（adapter 内会做结构校验）。
SEND_JSON="$(bash "${SCRIPT_DIR}/send_packet.sh" "${PAYLOAD}")"
# 第三步：立即拉取通知缓冲，避免消息堆积。
PULL_JSON="$(bash "${SCRIPT_DIR}/ws_pull_notify.sh" "${PULL_LIMIT}" "${CLEAR_NOTIFY}")"

python3 - "${CONNECT_JSON}" "${SEND_JSON}" "${PULL_JSON}" <<'PY'
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
send = parse_json(sys.argv[2], "chat.ws.request.send")
pull = parse_json(sys.argv[3], "chat.ws.notify.pull")

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
        "steps": {
            "connect": connect,
            "send": send,
            "pull": pull,
        },
    },
    "meta": {
        "flow": ["connect", "send", "pull"],
    },
    "error": error,
}
print(json.dumps(result, ensure_ascii=False))
PY
