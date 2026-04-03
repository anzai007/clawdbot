"""grindr_adapter 响应工具模块。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """返回 UTC ISO 时间戳。"""

    return datetime.now(timezone.utc).isoformat()


def build_success_response(action: str, data: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造统一成功响应。"""

    return {
        "action": action,
        "success": True,
        "data": data,
        "meta": meta or {},
        "error": None,
    }


def build_error_response(
    *,
    action: str,
    code: str,
    message: str,
    http_status: int,
    retry_count: int,
    endpoint: str,
) -> dict[str, Any]:
    """构造统一失败响应。"""

    return {
        "action": action,
        "success": False,
        "data": None,
        "meta": {
            "httpStatus": http_status,
            "retryCount": retry_count,
            "endpoint": endpoint,
            "timestamp": now_iso(),
        },
        "error": {
            "code": code,
            "message": message,
        },
    }
