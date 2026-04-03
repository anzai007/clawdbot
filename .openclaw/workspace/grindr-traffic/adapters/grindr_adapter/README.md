# grindr_adapter（可运行版）

## 项目简介
`grindr_adapter` 是 `grindr-profile-manager` 的本地 HTTP 适配层。
当前实现支持最小可运行能力：
- Flask 服务
- 统一响应结构
- 上游 GET/PUT 封装
- 超时/连接/5xx 重试
- 输入校验与 preview 预览
- 文件日志记录（不落地 secrets）

## 目录结构
```text
adapters/grindr_adapter/
├── app.py          # Flask 路由与统一错误处理
├── client.py       # 上游请求封装（headers/timeout/retry）
├── config.py       # .secrets/grindr.env 配置加载与校验
├── logger.py       # 文件日志与动作日志
├── schemas.py      # 输入校验与 preview 摘要
├── utils.py        # 统一成功/失败响应构造
├── requirements.txt
└── README.md
```

## 启动方式
1. 在工作区准备环境文件：
   - `.secrets/grindr.env`
   - 可参考 `.secrets/grindr.env.example`
2. 安装依赖：
   ```bash
   pip install -r adapters/grindr_adapter/requirements.txt
   ```
3. 启动服务：
   ```bash
   python adapters/grindr_adapter/app.py
   ```
   或：
   ```bash
   bash scripts/start_grindr_adapter.sh
   ```

## 已实现路由
- `POST /profile/me/get` -> 上游 `GET /v4/me/profile`
- `POST /profile/user/get` -> 上游 `GET /v7/profiles/{profileId}`
- `POST /profile/me/update` -> 上游 `PUT /v3.1/me/profile`
- `POST /profile/me/images/update` -> 上游 `PUT /v3/me/profile/images`
- `POST /profile/me/update/preview` -> 本地预览（不请求上游）
- `POST /profile/me/images/update/preview` -> 本地预览（不请求上游）

## 注意事项
- 配置缺失会在启动阶段直接报错并退出。
- 默认监听 `127.0.0.1:18081`。
- 为避免敏感信息泄露，日志中不记录 token 与 headers。
