---
name: grindr-profile-manager
version: 0.2.0
description: 通过本地 adapter 管理 Grindr 账号资料（读取、预览、更新）。
author: local
---

# grindr-profile-manager

## 技能名称
- `grindr-profile-manager`

## 适用场景
- 仅用于单账号资料管理：读取资料、预览更新、提交更新。
- 适用于资料文本与资料图片的低频维护。
- 所有动作都通过本地 adapter (`127.0.0.1:8787`) 转发。

## 不适用场景
- 不适用于批量互动、批量触达、群发行为。
- 不适用于高频重复修改资料。
- 不适用于任何需要直接访问 Grindr 上游 API 的场景。

## 支持动作
- 获取当前账号资料
- 获取指定用户资料（按 `profileId`）
- 预览资料文本更新（本地校验，不请求上游）
- 预览资料图片更新（本地校验，不请求上游）
- 提交资料文本更新
- 提交资料图片更新

## 输入示例
```bash
# profileId 查询
'{"profileId":827555450}'

# 文本更新
'{"displayName":"Alex","aboutMe":"hello"}'

# 图片更新
'{"primaryImageHash":"abc123","secondaryImageHashes":["s1","s2"]}'
```

## 执行命令
```bash
# 在 .openclaw/workspace/grindr-traffic 目录执行
bash skills/grindr-profile-manager/scripts/preview_update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-profile-manager/scripts/preview_update_profile_images.sh '{"primaryImageHash":"abc123"}'

bash skills/grindr-profile-manager/scripts/get_me_profile.sh
bash skills/grindr-profile-manager/scripts/get_user_profile.sh '{"profileId":827555450}'

bash skills/grindr-profile-manager/scripts/update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-profile-manager/scripts/update_profile_images.sh '{"primaryImageHash":"abc123"}'
```

## 执行规则
- mutation（`update_*`）前，必须先执行对应 `preview_*`。
- `preview_*` 通过后，再执行正式更新。
- 任意更新失败时，先停止重试并检查输入与 adapter 状态。
- 单用户资料查询（`profileId`）应直接调用 `get_user_profile.sh` 一次完成，避免额外探测与二次脚本拼接。

## 安全规则
- 禁止泄露 `.secrets/grindr.env` 中任何 secret。
- 脚本仅请求本地 adapter，禁止直接调用 Grindr 上游 API。
- 不允许高频重复修改，避免触发风险控制。
- 记录日志时必须脱敏，不输出 token/device id。

## 启动前置
```bash
bash scripts/start_grindr_adapter.sh
```
