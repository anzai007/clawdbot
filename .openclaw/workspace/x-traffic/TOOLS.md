# TOOLS.md - 工具与环境说明（X平台流量运营）

## 目标

记录 X 运营执行工具与调用规范，确保“可执行、可复现、可排障”。

## 常用能力

- TweetAPI skill：`skills/tweetapi/scripts/tweetapi.py`
- Telegram 渠道：`accountId=xtraffic`
- OpenClaw 技能目录：`workspace/x-traffic/skills/`

## TweetAPI 调用规范

- 基础变量：`TWEETAPI_KEY`、`TWEETAPI_BASE_URL`
- 业务参数：`authToken`、`proxy`
- 接口方法必须与文档一致（例如 `tweet/details` 用 GET）
- 先可选 `--dry-run` 验证参数，再执行真实请求

## 常见故障与处理

- `404 Not found`：路径或 HTTP 方法错误
- `400` 参数错误：按报错字段修正（如 `listId` 必须为数字）
- `403 code 226`：X 风控，需更换代理策略或账号环境
- `401 No token provided`：API密钥无效或端点错误

## 成功案例

### 发帖接口
- 端点：`POST /tw-v2/interaction/create-post`
- 示例：
```bash
cd skills/tweetapi && TWEETAPI_KEY="sk_xxx" python3 scripts/tweetapi.py request POST /tw-v2/interaction/create-post --json '{"authToken": "xxx", "text": "内容", "proxy": "host:port@user:pass"}'
```
- 成功返回：
```json
{"data":{"id":"推文ID","action":"create_tweet","success":true,"metadata":{"tweet_id":"xxx","author_username":"xxx","text":"xxx","url":"https://twitter.com/xxx/status/xxx"}}}
```

### 关注接口
- 端点：`POST /tw-v2/interaction/follow`
- 重要差异：文档显示使用`username`参数，实际需要`userId`参数（需先通过`/tw-v2/users/show`查询）
- 正确参数结构：
```bash
# 1. 先获取用户ID
cd skills/tweetapi && TWEETAPI_KEY="sk_xxx" python3 scripts/tweetapi.py request GET /tw-v2/users/show --json '{"authToken": "xxx", "username": "目标用户名", "proxy": "host:port@user:pass"}'
# 返回中包含 id_str 字段

# 2. 使用userId关注
cd skills/tweetapi && TWEETAPI_KEY="sk_xxx" python3 scripts/tweetapi.py request POST /tw-v2/interaction/follow --json '{"authToken": "xxx", "proxy": "host:port@user:pass", "body": {"userId": "查询到的用户ID"}}'
```
- 成功返回：
```json
{"success":true,"message":"关注成功"}
```

### 媒体上传与发帖接口
- 文档：https://www.tweetapi.com/docs/community/create-community-post-with-media
- 发送带媒体（图片/视频）的推文
- **两步流程**：
  1. **上传媒体**：`POST /tw-v2/media/upload` 上传文件，获取media_id
  2. **创建带媒体帖子**：`POST /tw-v2/community/create-post-with-media` 使用media_id
- **参数结构**：
```bash
# 1. 上传媒体（以图片为例）
cd skills/tweetapi && TWEETAPI_KEY="sk_xxx" python3 scripts/tweetapi.py request POST /tw-v2/media/upload --json '{"authToken": "xxx", "proxy": "host:port@user:pass", "body": {"media": "图片base64编码", "media_type": "image/jpeg"}}'

# 2. 创建带媒体帖子
cd skills/tweetapi && TWEETAPI_KEY="sk_xxx" python3 scripts/tweetapi.py request POST /tw-v2/community/create-post-with-media --json '{"authToken": "xxx", "proxy": "host:port@user:pass", "body": {"text": "推文内容", "media_ids": ["上传返回的media_id"]}}'
```
- **注意事项**：
  - 视频文件可能需要特殊处理（格式、大小限制）
  - 社区帖子接口可能也适用于普通时间线推文
  - base64编码需要包含完整图片数据

## 维护规则

- 新增接口能力时在此补充"示例命令 + 失败案例 + 成功返回"。
- 能沉淀为 SOP 的步骤，优先写入本文件。
