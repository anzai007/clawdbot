"""grindr_adapter FastAPI 入口（骨架）。"""

from __future__ import annotations

from fastapi import FastAPI

from client import GrindrClient
from config import load_settings
from logger import get_logger
from schemas import ProfileImageUpdateRequest, ProfileUpdateRequest
from utils import build_response

logger = get_logger()
settings = load_settings()
client = GrindrClient(settings)

app = FastAPI(title="grindr_adapter", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """健康检查路由。"""

    return build_response(ok=True, action="health", data={"service": "grindr_adapter"}, message="ok")


@app.get("/v1/profile/me")
def get_me_profile() -> dict:
    """获取当前账号资料（占位路由）。"""

    data = client.get_me_profile()
    return build_response(ok=True, action="get_me_profile", data=data, message="placeholder")


@app.get("/v1/profile/{user_id}")
def get_user_profile(user_id: str) -> dict:
    """获取指定用户资料（占位路由）。"""

    data = client.get_user_profile(user_id)
    return build_response(ok=True, action="get_user_profile", data=data, message="placeholder")


@app.post("/v1/profile/update")
def update_profile(req: ProfileUpdateRequest) -> dict:
    """更新资料文本（占位路由）。"""

    data = client.update_profile(req.model_dump())
    return build_response(ok=True, action="update_profile", data=data, message="placeholder")


@app.post("/v1/profile/images/update")
def update_profile_images(req: ProfileImageUpdateRequest) -> dict:
    """更新资料图片（占位路由）。"""

    data = client.update_profile_images(req.model_dump())
    return build_response(ok=True, action="update_profile_images", data=data, message="placeholder")


@app.post("/v1/profile/update/preview")
def preview_update_profile(req: ProfileUpdateRequest) -> dict:
    """预览资料文本更新（占位路由）。"""

    return build_response(
        ok=True,
        action="preview_update_profile",
        data={"preview": req.model_dump()},
        message="placeholder",
    )


@app.post("/v1/profile/images/update/preview")
def preview_update_profile_images(req: ProfileImageUpdateRequest) -> dict:
    """预览资料图片更新（占位路由）。"""

    return build_response(
        ok=True,
        action="preview_update_profile_images",
        data={"preview": req.model_dump()},
        message="placeholder",
    )
