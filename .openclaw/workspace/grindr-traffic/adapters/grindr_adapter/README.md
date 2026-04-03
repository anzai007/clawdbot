# grindr_adapter（可运行版）

## 项目简介
`grindr_adapter` 是 `grindr-profile-manager` 的本地 HTTP 适配层。
当前实现：
- Flask 轻量服务
- 统一响应结构
- 通过 requests 封装上游 GET/PUT
- timeout/connection/5xx 重试（4xx 不重试）
- 输入校验 + preview（本地校验，不请求上游）
- 文件日志（不记录 secrets）

## 目录结构
```text
adapters/grindr_adapter/
├── app.py
├── client.py
├── config.py
├── logger.py
├── schemas.py
├── utils.py
├── requirements.txt
└── README.md
```

## 完整启动步骤
1. 进入工作区：
   ```bash
   cd .openclaw/workspace/grindr-traffic
   ```
2. 准备环境文件：
   ```bash
   cp .secrets/grindr.env.example .secrets/grindr.env
   ```
3. 安装依赖（本机运行时）：
   ```bash
   python3 -m pip install -r adapters/grindr_adapter/requirements.txt
   ```
4. 启动 adapter（默认 `127.0.0.1:8787`）：
   ```bash
   bash scripts/start_grindr_adapter.sh
   ```
5. 健康检查：
   ```bash
   curl http://127.0.0.1:8787/health
   ```

## Docker 运行
```bash
docker compose build grindr-adapter
docker compose up -d grindr-adapter
curl http://127.0.0.1:8787/health
```

## Shell 调用示例
```bash
# 读取当前资料
bash skills/grindr-profile-manager/scripts/get_me_profile.sh

# 读取指定资料
bash skills/grindr-profile-manager/scripts/get_user_profile.sh '{"profileId":827555450}'

# 正式更新（务必先 preview）
bash skills/grindr-profile-manager/scripts/update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-profile-manager/scripts/update_profile_images.sh '{"primaryImageHash":"abc123"}'
```

## Preview 示例
```bash
bash skills/grindr-profile-manager/scripts/preview_update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-profile-manager/scripts/preview_update_profile_images.sh '{"primaryImageHash":"abc123"}'
```

## 常见错误
- `MISSING_PAYLOAD`：脚本缺少 JSON 参数。
- `ADAPTER_UNREACHABLE`：本地 adapter 未启动或端口不对。
- `CONFIG_ERROR`：`.secrets/grindr.env` 缺失或含 `replace_me`。
- `HTTP_4xx/5xx`：上游返回错误，检查 token、device id、payload。

## 联调顺序建议
1. 先启动 adapter（`bash scripts/start_grindr_adapter.sh`）
2. 跑 preview（文本 / 图片）
3. 跑 `get_me_profile`
4. 跑 `get_user_profile`
5. 最后跑 `update_*`

## 端口与路径约定
- adapter 本地固定：`127.0.0.1:8787`
- shell 脚本固定调用 `http://127.0.0.1:8787/...`
- 默认环境文件：`.openclaw/workspace/grindr-traffic/.secrets/grindr.env`
