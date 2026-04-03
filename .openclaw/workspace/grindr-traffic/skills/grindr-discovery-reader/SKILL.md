---
name: grindr-discovery-reader
version: 0.2.0
description: 读取 Grindr 发现页数据（附近用户、看过我的、指定用户资料）。
author: local
---

# grindr-discovery-reader

## Skill 名称
- `grindr-discovery-reader`

## 适用场景
- 仅读取发现页相关数据，不做任何资料修改或互动动作。
- 通过本地 adapter（`127.0.0.1:8787`）统一转发请求。

## 支持动作
- 读取附近用户列表
- 读取看过我的列表
- 读取指定用户资料（按 `profileId`）

## 输入示例
```bash
# 附近用户（可选）
'{"limit":30,"cursor":"optional_cursor"}'

# 看过我的（可选，支持 pageNumber）
'{"pageNumber":1,"limit":30}'

# 指定用户资料（必填 profileId）
'{"profileId":827555450}'
```

## 执行命令
```bash
# 在 .openclaw/workspace/grindr-traffic 目录执行
bash skills/grindr-discovery-reader/scripts/get_nearby_profiles.sh '{"limit":30}'
bash skills/grindr-discovery-reader/scripts/get_viewed_me.sh '{"pageNumber":1}'
bash skills/grindr-discovery-reader/scripts/get_user_profile.sh '{"profileId":827555450}'
```

## 路由映射
- `get_nearby_profiles.sh` -> `POST /discovery/nearby/get`
- `get_viewed_me.sh` -> `POST /discovery/viewed-me/get`
- `get_user_profile.sh` -> `POST /discovery/user/get`

## 安全规则
- 仅允许读取，不允许 mutation 行为。
- 禁止直接调用 Grindr 上游 API，必须走本地 adapter。
- 禁止泄露 `.secrets/grindr.env` 中的 secret 与 token。
- 遇到频率限制或风控提示，停止重试并上报。
