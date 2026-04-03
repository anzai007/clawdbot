# grindr-session-auth

## Skill 名称
`grindr-session-auth`

## 适用场景
- 仅用于 Grindr 账号会话管理：登录、会话状态读取、会话刷新、会话保存。
- 为其他业务 skill 提供会话凭据（`session`）读取能力。
- 通过本地 `grindr_adapter` (`127.0.0.1:8787`) 统一访问，不直接请求上游 API。

## 支持动作
- `get_session_status`：读取本地会话文件状态。
- `preview_login_password`：预览账号密码登录参数。
- `login_password`：账号密码登录。
- `preview_login_thirdparty`：预览第三方登录参数。
- `login_thirdparty`：第三方登录。
- `refresh_session`：刷新会话。
- `refresh_thirdparty_session`：刷新第三方会话。
- `save_session`：手动保存会话到本地 session 文件。

## 输入示例
```json
{"email":"user@example.com","password":"secret","token":"optional_client_token","geohash":"optional_geohash"}
```

```json
{"thirdPartyVendor":2,"thirdPartyToken":"thirdparty_token","geohash":"optional_geohash"}
```

```json
{"authToken":"existing_auth_token","token":"optional_client_token","email":"user@example.com","geohash":"optional_geohash"}
```

```json
{"authToken":"existing_auth_token","thirdPartyUserId":"google_xxx","geohash":"optional_geohash"}
```

```json
{"authToken":"replace_me","sessionToken":"replace_me","thirdPartyUserId":"google_xxx","source":"manual"}
```

## 执行命令
```bash
bash skills/grindr-session-auth/scripts/get_session_status.sh
bash skills/grindr-session-auth/scripts/preview_login_password.sh '{"email":"user@example.com","password":"secret"}'
bash skills/grindr-session-auth/scripts/login_password.sh '{"email":"user@example.com","password":"secret"}'
bash skills/grindr-session-auth/scripts/preview_login_thirdparty.sh '{"thirdPartyVendor":2,"thirdPartyToken":"thirdparty_token"}'
bash skills/grindr-session-auth/scripts/login_thirdparty.sh '{"thirdPartyVendor":2,"thirdPartyToken":"thirdparty_token"}'
bash skills/grindr-session-auth/scripts/refresh_session.sh '{"authToken":"existing_auth_token"}'
bash skills/grindr-session-auth/scripts/refresh_thirdparty_session.sh '{"authToken":"existing_auth_token","thirdPartyUserId":"google_xxx"}'
bash skills/grindr-session-auth/scripts/save_session.sh '{"authToken":"replace_me","sessionToken":"replace_me","source":"manual"}'
```

## 安全规则
- 登录前优先调用 `preview_*`，确认参数结构后再执行真实登录或刷新。
- 本 skill 只用于账号会话管理，不处理消息发送、互动、内容生成等业务动作。
- 不适用于批量账号管理，不允许并行批量登录。
- 不允许高频重复登录或刷新，避免触发平台风控。
- 不允许泄露账号密码、`authToken`、`sessionToken`、第三方令牌。
- 其他业务 skill 只读取 session，不自己执行登录。
