# grindr_adapter（工程骨架）

## 项目简介
`grindr_adapter` 是 `grindr-profile-manager` Skill 的本地适配器骨架。
当前版本只提供 FastAPI 路由占位、统一 JSON 返回结构和配置加载，不实现真实上游 HTTP 请求。

## 目录结构
```text
adapters/grindr_adapter/
├── app.py
├── client.py
├── config.py
├── logger.py
├── schemas.py
├── utils.py
└── requirements.txt
```

## 启动方式
1. 准备环境变量：
   - 复制 `.secrets/grindr.env.example` 为 `.secrets/grindr.env`
2. 安装依赖：
   - `pip install -r adapters/grindr_adapter/requirements.txt`
3. 启动服务：
   - `bash scripts/start_grindr_adapter.sh`
4. 验证健康检查：
   - `GET /health`

## 后续待实现点
- 在 `client.py` 中补齐真实上游请求与重试策略。
- 增加鉴权中间件与请求签名校验。
- 增加输入校验与错误码映射。
- 增加单元测试与集成测试。
- 对接 Skill 脚本与 Adapter 路由的完整闭环。
