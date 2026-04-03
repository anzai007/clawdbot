# grindr_adapter（profile + session-auth 可运行版）

## 项目简介
`grindr_adapter` 是 `grindr-traffic` 工作区中唯一的 Grindr 适配层，统一服务三个 skill：
- `grindr-profile-manager`：资料读取、预览、更新。
- `grindr-session-auth`：会话状态、登录、刷新、保存。
- `grindr-discovery-reader`：附近用户、看过我的、指定用户资料读取。

目标：
- 所有 skill 均只走 localhost adapter，不直接请求上游。
- 统一输入校验、统一 JSON 返回、统一错误结构。
- 会话与 token 默认按脱敏策略对外返回。

## 目录结构
```text
adapters/grindr_adapter/
├── app.py
├── client.py
├── config.py
├── logger.py
├── schemas.py
├── session_store.py
├── utils.py
├── requirements.txt
└── README.md
```

## 路径与端口约定
- env 文件：`.openclaw/workspace/grindr-traffic/.secrets/grindr.env`
- session 文件：由 `GRINDR_SESSION_FILE` 指定（默认 `./.secrets/grindr.session.json`）
- adapter 监听：`127.0.0.1:8787`
- skill 固定请求：`http://127.0.0.1:8787/...`
- discovery 上游 endpoint（可选）：
  - `GRINDR_DISCOVERY_NEARBY_ENDPOINT`（默认 `/v1/cascade`）
  - `GRINDR_DISCOVERY_VIEWED_ME_ENDPOINT`（默认 `/v7/views/list`）

## 完整启动步骤
1. 进入工作区：
   ```bash
   cd .openclaw/workspace/grindr-traffic
   ```
2. 准备配置文件：
   ```bash
   cp .secrets/grindr.env.example .secrets/grindr.env
   cp .secrets/grindr.session.json.example .secrets/grindr.session.json
   ```
3. 安装依赖：
   ```bash
   python3 -m pip install -r adapters/grindr_adapter/requirements.txt
   ```
4. 启动 adapter（默认 `127.0.0.1:8787`）：
   ```bash
   bash scripts/start_grindr_adapter.sh
   ```
5. 健康检查：
   ```bash
   curl -sS http://127.0.0.1:8787/health
   ```

## Profile Manager 路由（grindr-profile-manager）
- `POST /profile/me/get`
- `POST /profile/user/get`
- `POST /profile/me/update`
- `POST /profile/me/images/update`
- `POST /profile/me/update/preview`
- `POST /profile/me/images/update/preview`

## Session Auth 路由（grindr-session-auth）
- `POST /auth/session/status`
- `POST /auth/login/password`
- `POST /auth/login/password/preview`
- `POST /auth/login/thirdparty`
- `POST /auth/login/thirdparty/preview`
- `POST /auth/session/refresh`
- `POST /auth/session/refresh/thirdparty`
- `POST /auth/session/save`

## Discovery Reader 路由（grindr-discovery-reader）
- `POST /discovery/nearby/get`
- `POST /discovery/viewed-me/get`
- `POST /discovery/user/get`

## Shell 调用示例
### profile-manager
```bash
bash skills/grindr-profile-manager/scripts/get_me_profile.sh
bash skills/grindr-profile-manager/scripts/get_user_profile.sh '{"profileId":827555450}'
bash skills/grindr-profile-manager/scripts/preview_update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-profile-manager/scripts/update_profile.sh '{"displayName":"Alex"}'
```

### session-auth
```bash
bash skills/grindr-session-auth/scripts/get_session_status.sh
bash skills/grindr-session-auth/scripts/preview_login_password.sh '{"email":"user@example.com","password":"secret"}'
bash skills/grindr-session-auth/scripts/login_password.sh '{"email":"user@example.com","password":"secret"}'
bash skills/grindr-session-auth/scripts/save_session.sh '{"authToken":"replace_me","sessionToken":"replace_me","source":"manual"}'
```

### discovery-reader
```bash
bash skills/grindr-discovery-reader/scripts/get_nearby_profiles.sh '{"limit":30}'
bash skills/grindr-discovery-reader/scripts/get_viewed_me.sh '{"limit":30}'
bash skills/grindr-discovery-reader/scripts/get_user_profile.sh '{"profileId":827555450}'
```

## Preview 示例
```bash
bash skills/grindr-profile-manager/scripts/preview_update_profile.sh '{"displayName":"Alex"}'
bash skills/grindr-session-auth/scripts/preview_login_password.sh '{"email":"user@example.com","password":"secret"}'
```

## 常见错误说明
- `MISSING_PAYLOAD`：脚本缺少 JSON 参数。
- `ADAPTER_UNREACHABLE`：adapter 未启动，或端口不是 `127.0.0.1:8787`。
- `INVALID_JSON`：请求体不是合法 JSON 对象。
- `MISSING_AUTH_TOKEN`：refresh 缺少可用 authToken。
- `HTTP_4xx / HTTP_5xx`：上游返回错误，检查账号、设备参数、风控状态。

## 联调顺序建议（session-auth）
1. 启动 adapter：`bash scripts/start_grindr_adapter.sh`
2. `preview_login_password`
3. `get_session_status`
4. `login_password`
5. `save_session`
6. `refresh_session` / `refresh_thirdparty_session`

## 安全说明
- 对外返回的 `authToken`、`sessionToken` 均为脱敏格式。
- 完整 token 只允许落在 session 文件，不打印到日志。
- `preview_*` 只做校验，不请求上游。
