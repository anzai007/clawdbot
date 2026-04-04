#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ADAPTER_BASE_URL="$("${WORKSPACE_DIR}/scripts/resolve_grindr_adapter_base_url.sh")"


# 读取附近用户列表：允许不传参数，默认空对象。
ACTION="discovery.get_nearby_profiles"
ENDPOINT="${ADAPTER_BASE_URL}/discovery/nearby/get"
PAYLOAD="${1:-{}}"

if [[ -z "${PAYLOAD}" ]]; then
  PAYLOAD='{}'
fi

# 业务规则：默认按请求 limit 做本地裁剪；若未提供 limit，则默认裁剪前 5 条。
DEFAULT_TOP_N="$(python3 - "${PAYLOAD}" <<'PY'
import json
import re
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
default_value = 5

payload = None
for candidate in (raw, raw.replace('\\"', '"')):
    try:
        parsed = json.loads(candidate)
        # 兼容被二次序列化的入参字符串，例如 "\"{...}\""。
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        payload = parsed
        break
    except Exception:
        continue

if payload is None:
    for candidate in (raw, raw.replace('\\"', '"')):
        match = re.search(r'["\\]?limit["\\]?\s*:\s*(\d+)', candidate)
        if match:
            print(match.group(1))
            raise SystemExit(0)
    print(default_value)
    raise SystemExit(0)

if isinstance(payload, dict):
    limit = payload.get("limit")
    if isinstance(limit, int) and limit >= 0:
        print(limit)
        raise SystemExit(0)
    if isinstance(limit, str) and limit.isdigit():
        print(limit)
        raise SystemExit(0)

print(default_value)
PY
)"

TOP_N_RAW="${2:-${DISCOVERY_NEARBY_TOP_N:-${DEFAULT_TOP_N}}}"
if ! [[ "${TOP_N_RAW}" =~ ^[0-9]+$ ]]; then
  cat <<JSON
{"action":"request.validation","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}","topN":"${TOP_N_RAW}"},"error":{"code":"INVALID_TOP_N","message":"topN 必须是大于等于 0 的整数"}}
JSON
  exit 0
fi
TOP_N="${TOP_N_RAW}"

RESP="$(curl -sS -X POST "${ENDPOINT}" -H 'Content-Type: application/json' -d "${PAYLOAD}" --max-time 20 2>/dev/null)" || {
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{"endpoint":"${ENDPOINT}"},"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter"}}
JSON
  exit 0
}

# 核心逻辑：仅在成功响应时裁剪 data.items，避免超大 JSON 直接进入对话。
FILTERED_RESP="$(printf '%s' "${RESP}" | python3 -c '
import json
import sys

top_n = int(sys.argv[1])
raw = sys.stdin.read()

try:
    body = json.loads(raw)
except json.JSONDecodeError:
    print(json.dumps({
        "action": "response.parse",
        "success": False,
        "data": None,
        "meta": {"topNApplied": top_n},
        "error": {"code": "INVALID_ADAPTER_JSON", "message": "adapter 返回的内容不是合法 JSON"},
    }, ensure_ascii=False))
    raise SystemExit(0)

if not isinstance(body, dict):
    print(json.dumps(body, ensure_ascii=False))
    raise SystemExit(0)

if body.get("success") is not True:
    print(json.dumps(body, ensure_ascii=False))
    raise SystemExit(0)

data = body.get("data")
if not isinstance(data, dict):
    print(json.dumps(body, ensure_ascii=False))
    raise SystemExit(0)

items = data.get("items")
if not isinstance(items, list):
    print(json.dumps(body, ensure_ascii=False))
    raise SystemExit(0)

before_count = len(items)
if top_n > 0:
    data["items"] = items[:top_n]

meta = body.get("meta")
if not isinstance(meta, dict):
    meta = {}
    body["meta"] = meta

meta["itemCountBeforeTopN"] = before_count
meta["itemCountAfterTopN"] = len(data.get("items", []))
meta["topNApplied"] = top_n
print(json.dumps(body, ensure_ascii=False))
' "${TOP_N}")"

printf '%s\n' "${FILTERED_RESP}"
