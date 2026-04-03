"""grindr_adapter Flask 应用入口。"""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any

from flask import Flask, jsonify, request

from client import GrindrClient, UpstreamRequestError
from config import ConfigError, load_settings
from logger import init_logger
from schemas import (
    ValidationError,
    build_preview_result,
    ensure_object,
    validate_auth_login_password_payload,
    validate_auth_login_thirdparty_payload,
    validate_auth_refresh_session_payload,
    validate_auth_refresh_thirdparty_payload,
    validate_auth_session_save_payload,
    validate_discovery_list_payload,
    validate_images_update_payload,
    validate_profile_id_payload,
    validate_update_payload,
)
from session_store import (
    SessionStoreError,
    extract_session_from_upstream,
    get_session_status,
    load_session_raw,
    save_session,
    summarize_upstream_body,
)
from utils import build_error_response, build_success_response

ACTION_ME_GET = "profile.me.get"
ACTION_USER_GET = "profile.user.get"
ACTION_ME_UPDATE = "profile.me.update"
ACTION_ME_IMAGES_UPDATE = "profile.me.images.update"
ACTION_ME_UPDATE_PREVIEW = "profile.me.update.preview"
ACTION_ME_IMAGES_UPDATE_PREVIEW = "profile.me.images.update.preview"
ACTION_DISCOVERY_NEARBY_GET = "discovery.nearby.get"
ACTION_DISCOVERY_VIEWED_ME_GET = "discovery.viewed_me.get"
ACTION_DISCOVERY_USER_PROFILE_GET = "discovery.user_profile.get"

ACTION_AUTH_SESSION_STATUS = "auth.session.status"
ACTION_AUTH_LOGIN_PASSWORD = "auth.login.password"
ACTION_AUTH_LOGIN_PASSWORD_PREVIEW = "auth.login.password.preview"
ACTION_AUTH_LOGIN_THIRDPARTY = "auth.login.thirdparty"
ACTION_AUTH_LOGIN_THIRDPARTY_PREVIEW = "auth.login.thirdparty.preview"
ACTION_AUTH_SESSION_REFRESH = "auth.session.refresh"
ACTION_AUTH_SESSION_REFRESH_THIRDPARTY = "auth.session.refresh.thirdparty"
ACTION_AUTH_SESSION_SAVE = "auth.session.save"


def _session_result_payload(
    *,
    session_file: str,
    upstream_body: Any,
    fallback_session: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """根据上游结果更新本地会话，并只返回脱敏结果。"""

    extracted = extract_session_from_upstream(upstream_body)
    merged = dict(fallback_session)
    merged.update(extracted)

    persisted = False
    if any(merged.get(key) for key in ("authToken", "sessionToken", "thirdPartyUserId")):
        save_session(session_file, merged, source=source, merge=True)
        persisted = True

    return {
        "persisted": persisted,
        "sessionStatus": get_session_status(session_file),
        "upstream": summarize_upstream_body(upstream_body),
    }


def _json_or_empty_object(raw: Any, *, action: str) -> dict[str, Any]:
    """读取请求体；空体按空对象处理，便于纯读取路由免参调用。"""

    if raw is None:
        return {}
    return ensure_object(raw, action=action)


def create_app() -> Flask:
    """创建 Flask 应用并注册路由。"""

    settings = load_settings()
    logger = init_logger(settings.grindr_log_dir)
    client = GrindrClient(settings, logger)

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    # ===== profile-manager 路由（保持兼容） =====
    @app.post("/profile/me/get")
    def profile_me_get():
        """获取当前账号资料。"""

        result = client.get("/v4/me/profile", action=ACTION_ME_GET, use_auth=True)
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
        result = client.get(endpoint, action=ACTION_USER_GET, use_auth=True)
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

        result = client.put("/v3.1/me/profile", action=ACTION_ME_UPDATE, payload=update_payload, use_auth=True)
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
            use_auth=True,
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

    # ===== discovery-reader 路由（读取能力） =====
    @app.post("/discovery/nearby/get")
    def discovery_nearby_get():
        """读取附近用户列表。"""

        raw = request.get_json(silent=True)
        payload = _json_or_empty_object(raw, action=ACTION_DISCOVERY_NEARBY_GET)
        checked = validate_discovery_list_payload(payload)

        result = client.get_with_query(
            settings.grindr_discovery_nearby_endpoint,
            action=ACTION_DISCOVERY_NEARBY_GET,
            query=checked,
            use_auth=True,
        )
        resp = build_success_response(
            ACTION_DISCOVERY_NEARBY_GET,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/discovery/viewed-me/get")
    def discovery_viewed_me_get():
        """读取看过我的列表。"""

        raw = request.get_json(silent=True)
        payload = _json_or_empty_object(raw, action=ACTION_DISCOVERY_VIEWED_ME_GET)
        checked = validate_discovery_list_payload(payload)

        result = client.get_with_query(
            settings.grindr_discovery_viewed_me_endpoint,
            action=ACTION_DISCOVERY_VIEWED_ME_GET,
            query=checked,
            use_auth=True,
        )
        resp = build_success_response(
            ACTION_DISCOVERY_VIEWED_ME_GET,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/discovery/user/get")
    def discovery_user_profile_get():
        """读取指定用户资料。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_DISCOVERY_USER_PROFILE_GET)
        profile_id = validate_profile_id_payload(payload)

        endpoint = f"/v7/profiles/{profile_id}"
        result = client.get(endpoint, action=ACTION_DISCOVERY_USER_PROFILE_GET, use_auth=True)
        resp = build_success_response(
            ACTION_DISCOVERY_USER_PROFILE_GET,
            data=result["body"],
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    # ===== session-auth 路由（新标准路由 + 旧路由兼容） =====
    @app.post("/auth/session/status")
    @app.post("/session/status/get")
    def auth_session_status():
        """读取本地会话状态。"""

        resp = build_success_response(
            ACTION_AUTH_SESSION_STATUS,
            data=get_session_status(settings.grindr_session_file),
            meta={"endpoint": "/auth/session/status"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/login/password/preview")
    @app.post("/session/login/password/preview")
    def auth_login_password_preview():
        """预览密码登录输入（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_LOGIN_PASSWORD_PREVIEW)
        checked = validate_auth_login_password_payload(payload)
        preview = build_preview_result(checked)

        resp = build_success_response(
            ACTION_AUTH_LOGIN_PASSWORD_PREVIEW,
            data=preview,
            meta={"endpoint": "preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/login/password")
    @app.post("/session/login/password")
    def auth_login_password():
        """密码登录并尝试更新本地会话。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_LOGIN_PASSWORD)
        checked = validate_auth_login_password_payload(payload)

        result = client.post(
            "/v8/sessions",
            action=ACTION_AUTH_LOGIN_PASSWORD,
            payload=checked,
            use_auth=False,
        )

        data = _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={"email": checked.get("email")},
            source="login_password",
        )
        resp = build_success_response(
            ACTION_AUTH_LOGIN_PASSWORD,
            data=data,
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/login/thirdparty/preview")
    @app.post("/session/login/thirdparty/preview")
    def auth_login_thirdparty_preview():
        """预览第三方登录输入（不请求上游）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_LOGIN_THIRDPARTY_PREVIEW)
        checked = validate_auth_login_thirdparty_payload(payload)
        preview = build_preview_result(checked)

        resp = build_success_response(
            ACTION_AUTH_LOGIN_THIRDPARTY_PREVIEW,
            data=preview,
            meta={"endpoint": "preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/login/thirdparty")
    @app.post("/session/login/thirdparty")
    def auth_login_thirdparty():
        """第三方登录并尝试更新本地会话。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_LOGIN_THIRDPARTY)
        checked = validate_auth_login_thirdparty_payload(payload)

        result = client.post(
            "/v8/sessions/thirdparty",
            action=ACTION_AUTH_LOGIN_THIRDPARTY,
            payload=checked,
            use_auth=False,
        )

        data = _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={"thirdPartyVendor": checked.get("thirdPartyVendor")},
            source="login_thirdparty",
        )
        resp = build_success_response(
            ACTION_AUTH_LOGIN_THIRDPARTY,
            data=data,
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/session/refresh")
    @app.post("/session/refresh")
    def auth_session_refresh():
        """刷新会话：支持 payload authToken 或本地已有 authToken。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_SESSION_REFRESH)
        local_session = load_session_raw(settings.grindr_session_file) or {}

        checked = validate_auth_refresh_session_payload(
            payload,
            has_local_auth_token=bool(local_session.get("authToken")),
        )
        resolved_auth_token = checked.get("authToken") or local_session.get("authToken")

        upstream_payload = dict(checked)
        if resolved_auth_token and "authToken" not in upstream_payload:
            upstream_payload["authToken"] = resolved_auth_token

        result = client.post(
            "/v8/sessions",
            action=ACTION_AUTH_SESSION_REFRESH,
            payload=upstream_payload,
            use_auth=bool(resolved_auth_token),
            auth_token=resolved_auth_token,
        )

        data = _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={
                "authToken": resolved_auth_token,
                "email": checked.get("email"),
            },
            source="refresh_session",
        )
        resp = build_success_response(
            ACTION_AUTH_SESSION_REFRESH,
            data=data,
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/session/refresh/thirdparty")
    @app.post("/session/refresh/thirdparty")
    def auth_session_refresh_thirdparty():
        """刷新第三方会话。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_SESSION_REFRESH_THIRDPARTY)
        checked = validate_auth_refresh_thirdparty_payload(payload)

        result = client.post(
            "/v8/sessions/thirdparty",
            action=ACTION_AUTH_SESSION_REFRESH_THIRDPARTY,
            payload=checked,
            use_auth=True,
            auth_token=checked["authToken"],
        )

        data = _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={
                "authToken": checked["authToken"],
                "thirdPartyUserId": checked["thirdPartyUserId"],
            },
            source="refresh_thirdparty_session",
        )
        resp = build_success_response(
            ACTION_AUTH_SESSION_REFRESH_THIRDPARTY,
            data=data,
            meta={
                "httpStatus": result["httpStatus"],
                "retryCount": result["retryCount"],
                "endpoint": result["endpoint"],
            },
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/auth/session/save")
    @app.post("/session/save")
    def auth_session_save():
        """保存会话数据到本地文件（仅返回脱敏结果）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_AUTH_SESSION_SAVE)
        checked = validate_auth_session_save_payload(payload)

        source = checked.get("source") if isinstance(checked.get("source"), str) else "manual"
        save_result = save_session(settings.grindr_session_file, checked, source=source, merge=True)

        resp = build_success_response(
            ACTION_AUTH_SESSION_SAVE,
            data={
                "saveResult": save_result,
                "sessionStatus": get_session_status(settings.grindr_session_file),
            },
            meta={"endpoint": "/auth/session/save"},
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
        # 启动期配置错误直接明确退出。
        print(f"[CONFIG_ERROR] {err}")
        raise SystemExit(1) from err
