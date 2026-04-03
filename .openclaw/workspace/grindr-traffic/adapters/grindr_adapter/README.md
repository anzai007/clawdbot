# grindr_adapter（profile + session-auth）

## 项目简介
`grindr_adapter` 是 `grindr-traffic` 工作区内唯一的 Grindr API 适配层。

当前状态：
- `grindr-profile-manager`：已具备基础可用路由（含 preview）。
- `grindr-session-auth`：本次新增骨架路由与会话文件存储占位，不包含完整登录/刷新上游逻辑。

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

## 启动方式
1. 进入工作区：
   ```bash
   cd .openclaw/workspace/grindr-traffic
   ```
2. 准备配置：
   ```bash
   cp .secrets/grindr.env.example .secrets/grindr.env
   cp .secrets/grindr.session.json.example .secrets/grindr.session.json
   ```
3. 安装依赖：
   ```bash
   python3 -m pip install -r adapters/grindr_adapter/requirements.txt
   ```
4. 启动服务（默认 `127.0.0.1:8787`）：
   ```bash
   bash scripts/start_grindr_adapter.sh
   ```
5. 健康检查：
   ```bash
   curl http://127.0.0.1:8787/health
   ```

## 骨架路由清单（session-auth）
- `POST /session/status/get`
- `POST /session/login/password`
- `POST /session/login/thirdparty`
- `POST /session/refresh`
- `POST /session/refresh/thirdparty`
- `POST /session/save`
- `POST /session/login/password/preview`
- `POST /session/login/thirdparty/preview`

说明：以上路由当前以输入校验、结构化回包、本地会话文件读写占位为主，不执行完整上游登录请求。

## 后续待实现点
- 接入真实上游登录、刷新接口（含错误码映射）。
- 会话文件加密与脱敏存储策略。
- 会话过期判断与自动续期。
- 对第三方登录供应商做更细粒度 schema 校验。
- 增加 session-auth 的集成测试与重试策略验证。
