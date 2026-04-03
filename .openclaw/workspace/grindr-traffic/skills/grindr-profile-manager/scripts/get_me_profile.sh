#!/usr/bin/env bash
set -euo pipefail

# 输入参数占位：允许传入 JSON 字符串
INPUT_JSON="${1:-{}}"

# 占位输出：后续替换为真实逻辑
cat <<JSON
{"ok":true,"action":"get_me_profile","input":${INPUT_JSON},"message":"placeholder"}
JSON
