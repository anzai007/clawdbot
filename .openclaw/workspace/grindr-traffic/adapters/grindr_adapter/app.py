"""grindr_adapter Flask 应用入口。"""

from __future__ import annotations

import os
from http import HTTPStatus

from flask import Flask, jsonify, request

from client import GrindrClient, UpstreamRequestError
from config import ConfigError, load_settings
from logger import init_logger
from schemas import (
    ValidationError,
    build_preview_result,
    build_session_preview_result,
    ensure_object,
    validate_login_password_payload,
    validate_login_thirdparty_payload,
    validate_images_update_payload,
    validate_profile_id_payload,
    validate_refresh_payload,
    validate_refresh_thirdparty_payload,
    validate_save_session_payload,
    validate_update_payload,
)
from session_store import SessionStoreError, get_session_status, save_session
from utils import build_error_response, build_success_response

ACTION_ME_GET = "profile.me.get"
ACTION_USER_GET = "profile.user.get"
ACTION_ME_UPDATE = "profile.me.update"
ACTION_ME_IMAGES_UPDATE = "profile.me.images.update"
ACTION_ME_UPDATE_PREVIEW = "profile.me.update.preview"
ACTION_ME_IMAGES_UPDATE_PREVIEW = "profile.me.images.update.preview"
ACTION_SESSION_STATUS_GET = "session.status.get"
ACTION_SESSION_LOGIN_PASSWORD = "session.login.password"
ACTION_SESSION_LOGIN_THIRDPARTY = "session.login.thirdparty"
ACTION_SESSION_REFRESH = "session.refresh"
ACTION_SESSION_REFRESH_THIRDPARTY = "session.refresh.thirdparty"
ACTION_SESSION_SAVE = "session.save"
ACTION_SESSION_LOGIN_PASSWORD_PREVIEW = "session.login.password.preview"
ACTION_SESSION_LOGIN_THIRDPARTY_PREVIEW = "session.login.thirdparty.preview"


def create_app() -> Flask:
    """创建 Flask 应用并注册路由。"""

    settings = load_settings()
    logger = init_logger(settings.grindr_log_dir)
    client = GrindrClient(settings, logger)

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.post("/profile/me/get")
    def profile_me_get():
        """获取当前账号资料。"""

        result = client.get("/v4/me/profile", action=ACTION_ME_GET)
        payload = build_success_response(
            ACTION_ME_GET,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(payload), HTTPStatus.OK

    @app.post("/profile/user/get")
    def profile_user_get():
        """根据 profileId 获取资料。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_USER_GET)
        profile_id = validate_profile_id_payload(payload)

        endpoint = f"/v7/profiles/{profile_id}"
        result = client.get(endpoint, action=ACTION_USER_GET)
        resp = build_success_response(
            ACTION_USER_GET,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/profile/me/update")
    def profile_me_update():
        """更新当前账号资料文本。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_ME_UPDATE)
        update_payload = validate_update_payload(payload)

        result = client.put("/v3.1/me/profile", action=ACTION_ME_UPDATE, payload=update_payload)
        resp = build_success_response(
            ACTION_ME_UPDATE,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/profile/me/images/update")
    def profile_me_images_update():
        """更新当前账号资料图片。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_ME_IMAGES_UPDATE)
        image_payload = validate_images_update_payload(payload)

        result = client.put(
            "/v3/me/profile/images",
            action=ACTION_ME_IMAGES_UPDATE,
            payload=image_payload,
        )
        resp = build_success_response(
            ACTION_ME_IMAGES_UPDATE,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/profile/me/update/preview")
    def profile_me_update_preview():
        """预览文本资料更新（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_ME_UPDATE_PREVIEW)
        checked = validate_update_payload(payload)
        preview = build_preview_result(checked)

        resp = build_success_response(ACTION_ME_UPDATE_PREVIEW, data=preview, meta={"endpoint": "preview"})
        return jsonify(resp), HTTPStatus.OK

    @app.post("/profile/me/images/update/preview")
    def profile_me_images_update_preview():
        """预览图片资料更新（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_ME_IMAGES_UPDATE_PREVIEW)
        checked = validate_images_update_payload(payload)
        preview = build_preview_result(checked)

        resp = build_success_response(
            ACTION_ME_IMAGES_UPDATE_PREVIEW,
            data=preview,
            meta={"endpoint": "preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/status/get")
    def session_status_get():
        """读取本地会话状态（骨架占位）。"""

        status = get_session_status(settings.grindr_session_file)
        resp = build_success_response(
            ACTION_SESSION_STATUS_GET,
            data={
                "status": status,
                "placeholder": True,
                "note": "骨架阶段：仅提供本地会话文件摘要",
            },
            meta={"endpoint": "/session/status/get"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/login/password/preview")
    def session_login_password_preview():
        """预览账号密码登录输入（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_LOGIN_PASSWORD_PREVIEW)
        checked = validate_login_password_payload(payload)
        preview = build_session_preview_result(checked)
        resp = build_success_response(
            ACTION_SESSION_LOGIN_PASSWORD_PREVIEW,
            data=preview,
            meta={"endpoint": "preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/login/thirdparty/preview")
    def session_login_thirdparty_preview():
        """预览第三方登录输入（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_LOGIN_THIRDPARTY_PREVIEW)
        checked = validate_login_thirdparty_payload(payload)
        preview = build_session_preview_result(checked)
        resp = build_success_response(
            ACTION_SESSION_LOGIN_THIRDPARTY_PREVIEW,
            data=preview,
            meta={"endpoint": "preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/login/password")
    def session_login_password():
        """账号密码登录占位路由。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_LOGIN_PASSWORD)
        checked = validate_login_password_payload(payload)
        resp = build_success_response(
            ACTION_SESSION_LOGIN_PASSWORD,
            data={
                "placeholder": True,
                "receivedFields": sorted(checked.keys()),
                "note": "骨架阶段未实现上游登录请求",
            },
            meta={"endpoint": "/session/login/password"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/login/thirdparty")
    def session_login_thirdparty():
        """第三方登录占位路由。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_LOGIN_THIRDPARTY)
        checked = validate_login_thirdparty_payload(payload)
        resp = build_success_response(
            ACTION_SESSION_LOGIN_THIRDPARTY,
            data={
                "placeholder": True,
                "receivedFields": sorted(checked.keys()),
                "note": "骨架阶段未实现上游第三方登录请求",
            },
            meta={"endpoint": "/session/login/thirdparty"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/refresh")
    def session_refresh():
        """会话刷新占位路由。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_REFRESH)
        checked = validate_refresh_payload(payload)
        resp = build_success_response(
            ACTION_SESSION_REFRESH,
            data={
                "placeholder": True,
                "receivedFields": sorted(checked.keys()),
                "note": "骨架阶段未实现上游刷新请求",
            },
            meta={"endpoint": "/session/refresh"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/refresh/thirdparty")
    def session_refresh_thirdparty():
        """第三方会话刷新占位路由。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_REFRESH_THIRDPARTY)
        checked = validate_refresh_thirdparty_payload(payload)
        resp = build_success_response(
            ACTION_SESSION_REFRESH_THIRDPARTY,
            data={
                "placeholder": True,
                "receivedFields": sorted(checked.keys()),
                "note": "骨架阶段未实现上游第三方刷新请求",
            },
            meta={"endpoint": "/session/refresh/thirdparty"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/session/save")
    def session_save():
        """保存会话到本地文件。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_SESSION_SAVE)
        checked = validate_save_session_payload(payload)
        result = save_session(settings.grindr_session_file, checked)
        resp = build_success_response(
            ACTION_SESSION_SAVE,
            data={
                "placeholder": True,
                "saveResult": result,
                "note": "骨架阶段仅实现本地会话文件保存",
            },
            meta={"endpoint": "/session/save"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.route("/health", methods=["GET", "POST"])
    def health():
        """健康检查路由。"""

        return jsonify(build_success_response("health", data={"status": "ok"}, meta={})), HTTPStatus.OK

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        """输入校验错误处理。"""

        payload = build_error_response(
            action="request.validation",
            code=err.code,
            message=err.message,
            http_status=err.http_status,
            retry_count=0,
            endpoint=request.path,
        )
        return jsonify(payload), err.http_status

    @app.errorhandler(UpstreamRequestError)
    def handle_upstream_error(err: UpstreamRequestError):
        """上游请求错误处理。"""

        payload = build_error_response(
            action="upstream.request",
            code=err.code,
            message=err.message,
            http_status=err.http_status,
            retry_count=err.retry_count,
            endpoint=err.endpoint,
        )
        return jsonify(payload), err.http_status

    @app.errorhandler(SessionStoreError)
    def handle_session_store_error(err: SessionStoreError):
        """会话文件读写错误处理。"""

        payload = build_error_response(
            action="session.store",
            code=err.code,
            message=err.message,
            http_status=err.http_status,
            retry_count=0,
            endpoint=request.path,
        )
        return jsonify(payload), err.http_status

    @app.errorhandler(Exception)
    def handle_unknown_error(err: Exception):
        """未知错误处理，不暴露 traceback。"""

        logger.exception("未处理异常：%s", err)
        payload = build_error_response(
            action="internal.error",
            code="INTERNAL_ERROR",
            message="服务内部错误",
            http_status=500,
            retry_count=0,
            endpoint=request.path,
        )
        return jsonify(payload), HTTPStatus.INTERNAL_SERVER_ERROR

    return app


def main() -> None:
    """命令行启动入口：python app.py。"""

    host = os.getenv("ADAPTER_HOST", "127.0.0.1")
    port = int(os.getenv("ADAPTER_PORT", "8787"))
    app = create_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    try:
        main()
    except ConfigError as err:
        # 启动期配置错误直接明确退出
        print(f"[CONFIG_ERROR] {err}")
        raise SystemExit(1) from err
