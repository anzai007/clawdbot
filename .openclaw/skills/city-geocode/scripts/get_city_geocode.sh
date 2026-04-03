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

if ! command -v jq >/dev/null 2>&1; then
  json_error "MISSING_DEPENDENCY" "未找到 jq，请先安装 jq"
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
  MESSAGE="$(jq -c . "$TMP_BODY" 2>/dev/null || cat "$TMP_BODY")"
  printf '{"success":false,"error":{"code":"HTTP_%s","message":"请求三方 API 失败","detail":%s}}\n' "$HTTP_STATUS" "$MESSAGE"
  exit 1
fi

# 只返回首条结果，避免多条候选影响上层消费。
if [ "$(jq 'length' "$TMP_BODY")" -eq 0 ]; then
  printf '{"lat":null,"long":null}\n'
  exit 0
fi

jq -c '
{
  lat: .[0].lat,
  long: .[0].lon
}
' "$TMP_BODY"
