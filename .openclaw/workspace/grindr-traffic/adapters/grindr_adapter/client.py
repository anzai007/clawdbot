"""grindr_adapter 上游客户端（骨架）。"""

from __future__ import annotations

from typing import Any

from config import Settings


class GrindrClient:
    """上游接口客户端占位类。

    注意：当前只返回占位数据，不发起真实 HTTP 请求。
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_me_profile(self) -> dict[str, Any]:
        """获取当前账号资料（占位）。"""

        return {"placeholder": True, "method": "get_me_profile"}

    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """获取指定用户资料（占位）。"""

        return {"placeholder": True, "method": "get_user_profile", "user_id": user_id}

    def update_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """更新文本资料（占位）。"""

        return {"placeholder": True, "method": "update_profile", "payload": payload}

    def update_profile_images(self, payload: dict[str, Any]) -> dict[str, Any]:
        """更新图片资料（占位）。"""

        return {"placeholder": True, "method": "update_profile_images", "payload": payload}
