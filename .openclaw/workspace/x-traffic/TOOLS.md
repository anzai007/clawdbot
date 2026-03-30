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

## 维护规则

- 新增接口能力时在此补充"示例命令 + 失败案例 + 成功返回"。
- 能沉淀为 SOP 的步骤，优先写入本文件。
