"""grindr_adapter 通用工具（骨架）。"""

from __future__ import annotations

from typing import Any


def build_response(*, ok: bool, action: str, data: dict[str, Any] | None = None, message: str = "") -> dict[str, Any]:
    """构建统一 JSON 响应结构。"""

    return {
        "ok": ok,
        "action": action,
        "data": data or {},
        "message": message,
    }
