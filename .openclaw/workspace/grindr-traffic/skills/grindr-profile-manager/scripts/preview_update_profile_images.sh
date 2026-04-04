#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ADAPTER_BASE_URL="$("${WORKSPACE_DIR}/scripts/resolve_grindr_adapter_base_url.sh")"


ADAPTER_URL="${ADAPTER_BASE_URL}/profile/me/images/update/preview"
PAYLOAD="${1:-}"

if [[ -z "${PAYLOAD}" ]]; then
  cat <<JSON
{"action":"preview_update_profile_images","success":false,"error":{"code":"MISSING_PAYLOAD","message":"缺少参数：请传入图片预览 JSON"}}
JSON
  exit 1
fi

response=""
if ! response="$(curl -sS -X POST "${ADAPTER_URL}" -H "Content-Type: application/json" --data "${PAYLOAD}" --max-time 20)"; then
  cat <<JSON
{"action":"preview_update_profile_images","success":false,"error":{"code":"ADAPTER_UNREACHABLE","message":"无法连接本地 adapter: ${ADAPTER_URL}"}}
JSON
  exit 1
fi

printf '%s\n' "${response}"
