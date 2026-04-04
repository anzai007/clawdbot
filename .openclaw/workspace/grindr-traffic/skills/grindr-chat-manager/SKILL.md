---
name: grindr-chat-manager
version: 0.1.0
description: 基于 WebSocket IM 协议的 Grindr 私信管理技能（骨架版）。
author: local
---

# grindr-chat-manager

## 技能名称
- `grindr-chat-manager`

## 适用场景
- 在 `grindr-traffic` 工作区内，对 IM 协议包做标准化构造与校验。
- 对消息动作（连接、发送、已读、撤回、删除、媒体发送）进行统一入口管理。
- 先通过 adapter 完成协议预校验，后续再接入真实 WS 长连发送。

## 当前阶段说明（骨架）
- 已提供协议字段校验与结构化脚本入口。
- 已支持 `GRINDR_IM_WS_BASE_URL` 配置读取。
- `send` 路由当前为骨架占位：返回“已校验未发送”。

## 支持动作
- 获取 WS 配置：`/chat/ws/config/get`
- 预览协议包：`/chat/ws/request/preview`
- 发送协议包（骨架占位）：`/chat/ws/request/send`
- 解析通知包：`/chat/ws/notify/parse`

## 支持的协议类型
- `userConnect`
- `userDisconnect`
- `userList`
- `userUpdateNotify`
- `messageSend`
- `messageSendedNotify`
- `messageRecvNotify`
- `messageReaded`
- `messageReadedNotify`
- `messageRecall`
- `messageRecallNotify`
- `messageDelete`
- `messageDeleteNotify`
- `grindrChatSendMedia`

## 输入示例
```bash
# 通用协议包（示例：在线用户列表）
'{"requestId":1,"source":"","type":"userList","data":[]}'

# 发送文本消息（messageSend）
'{"requestId":2,"source":"","type":"messageSend","data":[{"messageId":"fdab55ee-2e77-43ea-b443-67b99a9146d9","conversationId":"110099028-111470292","sender":"110099028","senderName":"euleina","senderAvatar":"","senderTime":"2025-12-18T10:32:51.035Z","target":"111470292","messageType":"text","messageContent":"hello","isRead":false,"isRecalled":false,"isDeleted":false}]}'
```

## 执行命令
```bash
# 在 .openclaw/workspace/grindr-traffic 目录执行
bash skills/grindr-chat-manager/scripts/get_ws_config.sh
bash skills/grindr-chat-manager/scripts/preview_packet.sh '{"requestId":1,"type":"userList","data":[]}'
bash skills/grindr-chat-manager/scripts/send_packet.sh '{"requestId":2,"type":"userConnect","data":[{"user":"110099028"}]}'

# 类型快捷脚本
bash skills/grindr-chat-manager/scripts/user_connect.sh 110099028
bash skills/grindr-chat-manager/scripts/user_disconnect.sh 110099028
bash skills/grindr-chat-manager/scripts/user_list.sh
bash skills/grindr-chat-manager/scripts/message_send_text.sh 110099028 111470292 "hello"
bash skills/grindr-chat-manager/scripts/message_readed.sh 110099028-111470292 110099028 2025-12-18T10:32:54.756Z
bash skills/grindr-chat-manager/scripts/message_recall.sh 110099028 fdab55ee-2e77-43ea-b443-67b99a9146d9
bash skills/grindr-chat-manager/scripts/message_delete.sh 110099028 fdab55ee-2e77-43ea-b443-67b99a9146d9
bash skills/grindr-chat-manager/scripts/send_media.sh 841060828 841066441 1768632626747 1958048941 false false
```

## 安全规则
- 仅允许调用本地 adapter（`127.0.0.1:8787` 或通过解析脚本得到的本地入口）。
- 禁止脚本直接连接第三方 WS 服务或直接请求上游业务 API。
- 禁止在输出与日志中暴露 token、账号密码、设备标识等敏感信息。
- 发送动作默认先走 `preview_packet.sh` 校验，再执行 `send_packet.sh`。
- 若需要真实 WS 长连，请在 adapter 内扩展，不得在 skill 脚本侧绕过适配层。
