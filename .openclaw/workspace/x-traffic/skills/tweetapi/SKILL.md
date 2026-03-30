---
name: tweetapi
description: 通过 TweetAPI (tweetapi.com) 的 X-API-Key 调用 X/Twitter 相关接口。适用于发帖、回复、私信、搜索等需要第三方 API Key 认证的场景。
---

# tweetapi

使用 `X-API-Key` 调用 TweetAPI。

## 环境变量

```bash
export TWEETAPI_KEY="你的_tweetapi_key"
# 可选：默认值是 https://api.tweetapi.com
export TWEETAPI_BASE_URL="https://api.tweetapi.com"
```

## 用法

```bash
python3 {baseDir}/scripts/tweetapi.py request GET /v1/xxx
python3 {baseDir}/scripts/tweetapi.py request POST /v1/xxx --json '{"a":1}'
python3 {baseDir}/scripts/tweetapi.py request POST /v1/xxx --json '{"a":1}' --dry-run
```

说明：
- `path` 请按 TweetAPI 文档填写（例如 docs 里的 endpoint 路径）。
- 认证头固定为 `X-API-Key: $TWEETAPI_KEY`。
- `--dry-run` 只打印请求，不会真实发送。
