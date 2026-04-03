---
name: grindr-profile-manager
version: 0.1.0
description: 管理 Grindr 个人资料读取与更新流程的本地技能骨架。
author: local
---

# grindr-profile-manager

## 技能名称
- `grindr-profile-manager`

## 适用场景
- 在本地自动化流程中，统一管理 Grindr 资料相关动作。
- 需要先预览再更新资料文本或图片时。
- 需要将“查看自己资料 / 查看目标用户资料 / 更新资料”拆分为标准命令时。

## 支持动作
- 获取当前账号资料（占位）
- 获取指定用户资料（占位）
- 更新个人资料文本（占位）
- 更新个人资料图片（占位）
- 预览资料文本更新（占位）
- 预览资料图片更新（占位）

## 输入示例
```bash
# 读取当前资料（示例输入）
{"trace_id":"demo-001"}

# 读取指定用户资料（示例输入）
{"user_id":"1234567890"}

# 更新文本资料（示例输入）
{"display_name":"Alex","about":"Hello world"}

# 更新图片资料（示例输入）
{"image_paths":["./assets/a.jpg","./assets/b.jpg"]}
```

## 执行命令
```bash
# 在 grindr-traffic 工作区执行
bash skills/grindr-profile-manager/scripts/get_me_profile.sh '{"trace_id":"demo-001"}'
bash skills/grindr-profile-manager/scripts/get_user_profile.sh '{"user_id":"1234567890"}'
bash skills/grindr-profile-manager/scripts/update_profile.sh '{"display_name":"Alex"}'
bash skills/grindr-profile-manager/scripts/update_profile_images.sh '{"image_paths":["./assets/a.jpg"]}'
bash skills/grindr-profile-manager/scripts/preview_update_profile.sh '{"display_name":"Alex"}'
bash skills/grindr-profile-manager/scripts/preview_update_profile_images.sh '{"image_paths":["./assets/a.jpg"]}'

# 启动本地 adapter
bash scripts/start_grindr_adapter.sh
```

## 安全规则
- 本技能仅部署在 `.openclaw/workspace/grindr-traffic`，默认只给 `grindr-traffic` agent 使用。
- 严禁在脚本输出中打印真实 `GRINDR_AUTH_TOKEN`。
- 所有外部更新动作应先走 preview，再进行正式 update。
- 生产环境必须启用最小权限、最小日志策略，不记录敏感头信息。
- 当前版本为工程骨架，返回占位结果，不执行真实上游请求。
