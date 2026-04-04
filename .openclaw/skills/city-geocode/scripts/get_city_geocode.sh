#!/usr/bin/env bash
set -euo pipefail

# 统一输出错误 JSON，便于上层 agent 直接消费。
json_error() {
  local code="$1"
  local message="$2"
  printf '{"success":false,"error":{"code":"%s","message":"%s"}}\n' "$code" "$message"
}

# 至少需要一个参数作为城市名，支持带空格城市（通过 "$*" 合并）。
if [ "$#" -lt 1 ]; then
  json_error "MISSING_CITY" "请提供城市名，例如：Tokyo"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  json_error "MISSING_DEPENDENCY" "未找到 curl，请先安装 curl"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  json_error "MISSING_DEPENDENCY" "未找到 python3，请先安装 python3"
  exit 1
fi

CITY_QUERY="$*"
API_URL="https://nominatim.openstreetmap.org/search"
TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

# 使用 URL 编码的 q 参数调用 Nominatim，格式固定为 JSON。
HTTP_STATUS="$(curl -sS -G "$API_URL" \
  --connect-timeout 5 \
  --max-time 20 \
  --data-urlencode "q=${CITY_QUERY}" \
  --data-urlencode "format=json" \
  --data-urlencode "limit=1" \
  -H "User-Agent: openclaw-city-geocode-skill/1.0" \
  -o "$TMP_BODY" \
  -w "%{http_code}")"

if [ "$HTTP_STATUS" -lt 200 ] || [ "$HTTP_STATUS" -ge 300 ]; then
  # 使用 Python 兼容 JSON/文本两类错误体，避免依赖 jq。
  python3 - "$HTTP_STATUS" "$TMP_BODY" <<'PY'
import json
import pathlib
import sys

status = sys.argv[1]
body_path = pathlib.Path(sys.argv[2])
raw = body_path.read_text(encoding="utf-8", errors="replace")
detail = raw
try:
    detail = json.loads(raw)
except Exception:
    detail = raw

print(
    json.dumps(
        {
            "success": False,
            "error": {
                "code": f"HTTP_{status}",
                "message": "请求三方 API 失败",
                "detail": detail,
            },
        },
        ensure_ascii=False,
    )
)
PY
  exit 1
fi

# 只返回首条结果（lat/long），避免多条候选影响上层消费。
python3 - "$TMP_BODY" <<'PY'
import json
import pathlib
import sys

body_path = pathlib.Path(sys.argv[1])
raw = body_path.read_text(encoding="utf-8", errors="replace")

try:
    payload = json.loads(raw)
except Exception:
    print(
        json.dumps(
            {
                "success": False,
                "error": {
                    "code": "INVALID_JSON",
                    "message": "三方 API 返回的不是合法 JSON",
                },
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(1)

if not isinstance(payload, list) or len(payload) == 0:
    print(json.dumps({"lat": None, "long": None}, ensure_ascii=False))
    raise SystemExit(0)

first = payload[0] if isinstance(payload[0], dict) else {}
print(
    json.dumps(
        {
            "lat": first.get("lat"),
            "long": first.get("lon"),
        },
        ensure_ascii=False,
    )
)
PY
