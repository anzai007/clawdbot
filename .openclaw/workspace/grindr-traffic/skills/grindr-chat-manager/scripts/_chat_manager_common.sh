#!/usr/bin/env bash
set -euo pipefail

# 解析本地 adapter 地址，保持与现有 grindr skill 一致。
resolve_adapter_base_url() {
  local script_dir workspace_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  workspace_dir="$(cd "${script_dir}/../../.." && pwd)"
  "${workspace_dir}/scripts/resolve_grindr_adapter_base_url.sh"
}

# 统一输出结构化错误 JSON。
json_error() {
  local action="$1"
  local endpoint="$2"
  local code="$3"
  local message="$4"
  cat <<JSON
{"action":"${action}","success":false,"data":null,"meta":{"endpoint":"${endpoint}"},"error":{"code":"${code}","message":"${message}"}}
JSON
}

# 统一 POST JSON 到 adapter。
post_json() {
  local action="$1"
  local endpoint="$2"
  local payload="$3"

  local resp
  if ! resp="$(curl -sS -X POST "${endpoint}" -H 'Content-Type: application/json' -d "${payload}" --max-time 20 2>/dev/null)"; then
    json_error "${action}" "${endpoint}" "ADAPTER_UNREACHABLE" "无法连接本地 adapter"
    return 0
  fi

  printf '%s\n' "${resp}"
}
