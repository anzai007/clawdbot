"""grindr_adapter 日志模块。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path


def init_logger(log_dir: str) -> logging.Logger:
    """初始化日志器：控制台 + 文件日志。"""

    logger = logging.getLogger("grindr_adapter")
    if logger.handlers:
        return logger

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(Path(log_dir) / "adapter.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)

    return logger


def _now_iso() -> str:
    """返回 UTC ISO 时间字符串。"""

    return datetime.now(timezone.utc).isoformat()


def log_action_event(
    logger: logging.Logger,
    *,
    action: str,
    endpoint: str,
    success: bool,
    http_status: int | None,
    retry_count: int,
    error_code: str | None,
) -> None:
    """记录动作日志。

    注意：不记录 token、headers、敏感 payload。
    """

    record = {
        "timestamp": _now_iso(),
        "action": action,
        "endpoint": endpoint,
        "success": success,
        "httpStatus": http_status,
        "retryCount": retry_count,
        "errorCode": error_code,
    }
    logger.info(json.dumps(record, ensure_ascii=False))
