"""grindr_adapter 数据结构定义（骨架）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """统一响应结构，保证脚本和 HTTP 返回格式一致。"""

    ok: bool = Field(..., description="请求是否成功")
    action: str = Field(..., description="动作名")
    data: dict[str, Any] = Field(default_factory=dict, description="动作返回数据")
    message: str = Field(default="", description="补充说明")


class ProfileUpdateRequest(BaseModel):
    """资料文本更新请求占位结构。"""

    display_name: str | None = None
    about: str | None = None


class ProfileImageUpdateRequest(BaseModel):
    """资料图片更新请求占位结构。"""

    image_paths: list[str] = Field(default_factory=list)
