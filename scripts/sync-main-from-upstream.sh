#!/usr/bin/env bash
set -euo pipefail

# 同步主分支脚本：
# 1) 确认 upstream/origin 远程存在（upstream 不存在时按默认仓库地址补齐）
# 2) 切换到 main 分支并拉取 upstream/main
# 3) 将本地 main rebase 到 upstream/main
# 4) 推送本地 main 到 origin/main

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_URL_DEFAULT="https://github.com/openclaw/openclaw.git"
UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-upstream}"
ORIGIN_REMOTE="${ORIGIN_REMOTE:-origin}"
TARGET_BRANCH="${TARGET_BRANCH:-main}"

cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "错误：当前目录不是 Git 仓库：$REPO_ROOT" >&2
  exit 1
fi

if ! git remote get-url "$ORIGIN_REMOTE" >/dev/null 2>&1; then
  echo "错误：未找到远程 '$ORIGIN_REMOTE'，请先配置 origin。" >&2
  exit 1
fi

if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
  echo "未检测到 '$UPSTREAM_REMOTE'，正在添加默认上游：$UPSTREAM_URL_DEFAULT"
  git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_URL_DEFAULT"
fi

echo "当前远程："
git remote -v

echo "切换到分支：$TARGET_BRANCH"
git checkout "$TARGET_BRANCH"

echo "拉取上游更新：$UPSTREAM_REMOTE/$TARGET_BRANCH"
git fetch "$UPSTREAM_REMOTE"

echo "重放本地提交到上游最新提交之上（rebase）"
git rebase "$UPSTREAM_REMOTE/$TARGET_BRANCH"

echo "推送到 fork：$ORIGIN_REMOTE/$TARGET_BRANCH"
git push "$ORIGIN_REMOTE" "$TARGET_BRANCH"

echo "完成：本地 $TARGET_BRANCH 已与 $UPSTREAM_REMOTE/$TARGET_BRANCH 对齐，并推送到 $ORIGIN_REMOTE/$TARGET_BRANCH。"
