#!/usr/bin/env bash
set -euo pipefail

# 城市 nearby 快路径：
# 1) 调用公用 city-geocode skill 获取经纬度
# 2) 调用当前 skill 的 get_nearby_profiles.sh 获取附近用户
# 3) 统一返回 JSON（包含请求城市与解析坐标）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CITY_GEOCODE_SCRIPT_CANDIDATE_1="${SCRIPT_DIR}/../../../../../skills/city-geocode/scripts/get_city_geocode.sh"
CITY_GEOCODE_SCRIPT_CANDIDATE_2="${HOME}/.openclaw/skills/city-geocode/scripts/get_city_geocode.sh"
ACTION="discovery.get_nearby_by_city"

CITY_GEOCODE_SCRIPT=""
if [[ -x "${CITY_GEOCODE_SCRIPT_CANDIDATE_1}" ]]; then
  CITY_GEOCODE_SCRIPT="${CITY_GEOCODE_SCRIPT_CANDIDATE_1}"
elif [[ -x "${CITY_GEOCODE_SCRIPT_CANDIDATE_2}" ]]; then
  CITY_GEOCODE_SCRIPT="${CITY_GEOCODE_SCRIPT_CANDIDATE_2}"
fi

json_error() {
  local code="$1"
  local message="$2"
  cat <<JSON
{"action":"${ACTION}","success":false,"data":null,"meta":{},"error":{"code":"${code}","message":"${message}"}}
JSON
}

if [[ "$#" -lt 1 ]]; then
  json_error "MISSING_CITY" "请提供城市名，例如：Tokyo"
  exit 0
fi

CITY="$1"
TOP_N_RAW="${2:-5}"
LIMIT_RAW="${3:-${TOP_N_RAW}}"

if ! [[ "${TOP_N_RAW}" =~ ^[0-9]+$ ]]; then
  json_error "INVALID_TOP_N" "topN 必须是大于等于 0 的整数"
  exit 0
fi
if ! [[ "${LIMIT_RAW}" =~ ^[0-9]+$ ]]; then
  json_error "INVALID_LIMIT" "limit 必须是大于等于 0 的整数"
  exit 0
fi

if [[ -z "${CITY_GEOCODE_SCRIPT}" ]]; then
  json_error "CITY_GEOCODE_NOT_FOUND" "未找到 city-geocode 脚本，请先检查 skill 安装"
  exit 0
fi

TMP_GEOCODE="$(mktemp)"
TMP_COORDS="$(mktemp)"
TMP_NEARBY="$(mktemp)"
trap 'rm -f "${TMP_GEOCODE}" "${TMP_COORDS}" "${TMP_NEARBY}"' EXIT

"${CITY_GEOCODE_SCRIPT}" "${CITY}" >"${TMP_GEOCODE}" 2>/dev/null || true

python3 - "${TMP_GEOCODE}" >"${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys

raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").strip()
if not raw:
    print(json.dumps({"ok": False, "code": "EMPTY_GEOCODE_RESPONSE", "message": "city-geocode 返回为空"}, ensure_ascii=False))
    raise SystemExit(0)

try:
    body = json.loads(raw)
except Exception:
    print(json.dumps({"ok": False, "code": "INVALID_GEOCODE_JSON", "message": "city-geocode 返回非 JSON"}, ensure_ascii=False))
    raise SystemExit(0)

if isinstance(body, dict) and body.get("success") is False:
    err = body.get("error") or {}
    print(json.dumps({
        "ok": False,
        "code": err.get("code", "GEOCODE_FAILED"),
        "message": err.get("message", "city-geocode 执行失败"),
    }, ensure_ascii=False))
    raise SystemExit(0)

if not isinstance(body, dict):
    print(json.dumps({"ok": False, "code": "INVALID_GEOCODE_BODY", "message": "city-geocode 返回结构异常"}, ensure_ascii=False))
    raise SystemExit(0)

lat = body.get("lat")
lng = body.get("long")
if lat in (None, "") or lng in (None, ""):
    print(json.dumps({"ok": False, "code": "CITY_NOT_FOUND", "message": "未查到城市对应经纬度"}, ensure_ascii=False))
    raise SystemExit(0)

try:
    lat_num = float(lat)
    lng_num = float(lng)
except Exception:
    print(json.dumps({"ok": False, "code": "INVALID_COORDINATES", "message": "city-geocode 返回的经纬度不是数字"}, ensure_ascii=False))
    raise SystemExit(0)

print(json.dumps({"ok": True, "lat": lat_num, "lng": lng_num}, ensure_ascii=False))
PY

COORDS_OK="$(python3 - "${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys
try:
    body = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace") or "{}")
except Exception:
    body = {}
print("1" if body.get("ok") is True else "0")
PY
)"

if [[ "${COORDS_OK}" != "1" ]]; then
  CODE="$(python3 - "${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys
try:
    body = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace") or "{}")
except Exception:
    body = {}
print(body.get("code", "GEOCODE_FAILED"))
PY
)"
  MESSAGE="$(python3 - "${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys
try:
    body = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace") or "{}")
except Exception:
    body = {}
print(body.get("message", "city-geocode 执行失败"))
PY
)"
  json_error "${CODE}" "${MESSAGE}"
  exit 0
fi

LAT="$(python3 - "${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys
body = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
print(body["lat"])
PY
)"
LNG="$(python3 - "${TMP_COORDS}" <<'PY'
import json
import pathlib
import sys
body = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
print(body["lng"])
PY
)"

PAYLOAD="$(python3 - "${LAT}" "${LNG}" "${LIMIT_RAW}" <<'PY'
import json
import sys
lat = float(sys.argv[1])
lng = float(sys.argv[2])
limit = int(sys.argv[3])
print(json.dumps({"lat": lat, "lng": lng, "limit": limit}, ensure_ascii=False))
PY
)"

bash "${SCRIPT_DIR}/get_nearby_profiles.sh" "${PAYLOAD}" "${TOP_N_RAW}" >"${TMP_NEARBY}" || true

python3 - "${TMP_NEARBY}" "${CITY}" "${LAT}" "${LNG}" "${TOP_N_RAW}" "${LIMIT_RAW}" <<'PY'
import json
import pathlib
import sys

raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
city = sys.argv[2]
lat = float(sys.argv[3])
lng = float(sys.argv[4])
top_n = int(sys.argv[5])
limit = int(sys.argv[6])

try:
    body = json.loads(raw)
except Exception:
    print(json.dumps({
        "action": "discovery.get_nearby_by_city",
        "success": False,
        "data": None,
        "meta": {"requestedCity": city},
        "error": {"code": "INVALID_NEARBY_JSON", "message": "nearby 脚本返回非 JSON"},
    }, ensure_ascii=False))
    raise SystemExit(0)

meta = body.get("meta")
if not isinstance(meta, dict):
    meta = {}
    body["meta"] = meta

meta["requestedCity"] = city
meta["resolvedCoordinates"] = {"lat": lat, "lng": lng}
meta["topNRequested"] = top_n
meta["limitRequested"] = limit
meta["fastPath"] = True

if "action" not in body:
    body["action"] = "discovery.get_nearby_by_city"

print(json.dumps(body, ensure_ascii=False))
PY
