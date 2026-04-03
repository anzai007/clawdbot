"""grindr_adapter 配置模块（骨架）。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """读取环境变量并提供给应用使用。"""

    grindr_base_url: str = os.getenv("GRINDR_BASE_URL", "https://grindr.mobi")
    grindr_auth_token: str = os.getenv("GRINDR_AUTH_TOKEN", "replace_me")
    grindr_device_id: str = os.getenv("GRINDR_DEVICE_ID", "replace_me")
    grindr_user_agent: str = os.getenv("GRINDR_USER_AGENT", "replace_me")
    grindr_timeout_seconds: int = int(os.getenv("GRINDR_TIMEOUT_SECONDS", "20"))
    grindr_retry_times: int = int(os.getenv("GRINDR_RETRY_TIMES", "2"))
    grindr_log_dir: str = os.getenv("GRINDR_LOG_DIR", "./logs")


def load_settings() -> Settings:
    """统一加载配置，便于后续注入。"""

    return Settings()
