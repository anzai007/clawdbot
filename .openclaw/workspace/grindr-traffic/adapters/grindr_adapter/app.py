"""grindr_adapter Flask 应用入口。"""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any, Callable

from flask import Flask, jsonify, request

from client import GrindrClient, UpstreamRequestError
from config import ConfigError, load_settings
from logger import init_logger
from schemas import (
    ValidationError,
    build_preview_result,
    ensure_object,
    validate_ws_packet_payload,
    validate_auth_login_password_payload,
    validate_auth_login_thirdparty_payload,
    validate_auth_refresh_session_payload,
    validate_auth_refresh_thirdparty_payload,
    validate_auth_session_save_payload,
    validate_discovery_list_payload,
    validate_images_update_payload,
    validate_profile_id_payload,
    validate_update_payload,
    ws_supported_types,
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
from ws_connection import WsConnectionError, WsConnectionManager

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
ACTION_AUTH_AUTO_REFRESH = "auth.auto.refresh"
ACTION_AUTH_AUTO_LOGIN_PASSWORD = "auth.auto.login.password"
ACTION_CHAT_WS_CONFIG_GET = "chat.ws.config.get"
ACTION_CHAT_WS_CONNECTION_STATUS = "chat.ws.connection.status"
ACTION_CHAT_WS_CONNECTION_CONNECT = "chat.ws.connection.connect"
ACTION_CHAT_WS_CONNECTION_DISCONNECT = "chat.ws.connection.disconnect"
ACTION_CHAT_WS_REQUEST_PREVIEW = "chat.ws.request.preview"
ACTION_CHAT_WS_REQUEST_SEND = "chat.ws.request.send"
ACTION_CHAT_WS_NOTIFY_PARSE = "chat.ws.notify.parse"
ACTION_CHAT_WS_NOTIFY_PULL = "chat.ws.notify.pull"

_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _encode_geohash(lat: float, lng: float, precision: int = 12) -> str:
    """把经纬度编码为 geohash。

    说明：
    - Postman 预处理脚本要求把 `lat/lng` 转成 `nearbyGeoHash`。
    - 这里使用标准 geohash 编码，不依赖额外三方库。
    """

    lat_interval = [-90.0, 90.0]
    lng_interval = [-180.0, 180.0]
    is_even_bit = True
    bit = 0
    ch = 0
    output: list[str] = []
    bits = (16, 8, 4, 2, 1)

    while len(output) < precision:
        if is_even_bit:
            mid = (lng_interval[0] + lng_interval[1]) / 2.0
            if lng >= mid:
                ch |= bits[bit]
                lng_interval[0] = mid
            else:
                lng_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2.0
            if lat >= mid:
                ch |= bits[bit]
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid

        is_even_bit = not is_even_bit
        if bit < 4:
            bit += 1
        else:
            output.append(_GEOHASH_BASE32[ch])
            bit = 0
            ch = 0

    return "".join(output)


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


def _prepare_nearby_query(payload: dict[str, Any], fallback_geohash: str) -> dict[str, Any]:
    """规范化附近列表查询参数。

    优先级：
    1. 直接传 `nearbyGeoHash`
    2. 传 `lat + lng/lon`，自动编码为 `nearbyGeoHash`
    3. 回退 `GRINDR_GEOHASH`
    """

    query = dict(payload)
    nearby_hash = query.get("nearbyGeoHash")
    if isinstance(nearby_hash, str) and nearby_hash.strip():
        query["nearbyGeoHash"] = nearby_hash.strip()
    else:
        lat_raw = query.pop("lat", None)
        lng_raw = query.pop("lng", query.pop("lon", None))
        if lat_raw is not None and lng_raw is not None:
            try:
                lat = float(lat_raw)
                lng = float(lng_raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError("INVALID_LOCATION", "lat/lng 必须是数字", http_status=400) from exc
            if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
                raise ValidationError("INVALID_LOCATION", "lat/lng 超出有效范围", http_status=400)
            query["nearbyGeoHash"] = _encode_geohash(lat, lng, precision=12)
        elif fallback_geohash.strip():
            query["nearbyGeoHash"] = fallback_geohash.strip()

    # 上游按 Postman 约定仅消费 nearbyGeoHash，不携带 lat/lng。
    query.pop("lat", None)
    query.pop("lng", None)
    query.pop("lon", None)
    return query


def create_app() -> Flask:
    """创建 Flask 应用并注册路由。"""

    settings = load_settings()
    logger = init_logger(settings.grindr_log_dir)
    client = GrindrClient(settings, logger)

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _load_runtime_session() -> dict[str, Any]:
        """读取本地会话；失败时返回空对象并记录告警。"""

        try:
            return load_session_raw(settings.grindr_session_file) or {}
        except SessionStoreError:
            # 会话文件异常时降级回退，避免读取类路由直接 500。
            logger.warning("自动补救：session 文件读取失败，回退到环境 token")
            return {}

    def _resolve_runtime_auth_token() -> str | None:
        """优先读取会话文件中的 authToken，回退到环境配置。"""

        session = _load_runtime_session()
        token = session.get("authToken")
        if isinstance(token, str) and token.strip():
            return token.strip()

        fallback = settings.grindr_auth_token.strip()
        return fallback or None

    def _resolve_runtime_session_token() -> str | None:
        """优先读取会话文件中的 sessionToken（对应 /v8/sessions 的 sessionId）。"""

        session = _load_runtime_session()
        token = session.get("sessionToken")
        if isinstance(token, str) and token.strip():
            return token.strip()

        # 兼容旧配置：未落 sessionToken 时回退 env token。
        fallback = settings.grindr_auth_token.strip()
        return fallback or None

    def _configured_geohash() -> str | None:
        """读取可选 geohash；自动鉴权链路会透传给 /v8/sessions。"""

        value = settings.grindr_geohash.strip()
        return value or None

    def _try_auto_refresh_session() -> bool:
        """尝试自动刷新会话（401 兜底第一步）。"""

        current_auth_token = _resolve_runtime_auth_token()
        if not current_auth_token:
            return False

        refresh_payload: dict[str, Any] = {"authToken": current_auth_token}
        local_session = _load_runtime_session()
        email = local_session.get("email")
        if isinstance(email, str) and email.strip():
            refresh_payload["email"] = email.strip()
        geohash = _configured_geohash()
        if geohash:
            refresh_payload["geohash"] = geohash

        try:
            result = client.post(
                "/v8/sessions",
                action=ACTION_AUTH_AUTO_REFRESH,
                payload=refresh_payload,
                use_auth=True,
                auth_token=current_auth_token,
            )
        except UpstreamRequestError:
            return False

        _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={"authToken": current_auth_token, "email": refresh_payload.get("email")},
            source="auto_refresh_401",
        )
        logger.info("401 自动补救：session refresh 成功")
        return True

    def _try_auto_login_password() -> bool:
        """尝试自动密码登录（401 兜底第二步）。"""

        email = settings.grindr_auto_login_email.strip()
        password = settings.grindr_auto_login_password.strip()
        if not email or not password:
            return False
        login_payload: dict[str, Any] = {"email": email, "password": password}
        geohash = _configured_geohash()
        if geohash:
            login_payload["geohash"] = geohash

        try:
            result = client.post(
                "/v8/sessions",
                action=ACTION_AUTH_AUTO_LOGIN_PASSWORD,
                payload=login_payload,
                use_auth=False,
            )
        except UpstreamRequestError:
            return False

        _session_result_payload(
            session_file=settings.grindr_session_file,
            upstream_body=result["body"],
            fallback_session={"email": email},
            source="auto_login_password_401",
        )
        logger.info("401 自动补救：password login 成功")
        return True

    def _try_auto_reauth() -> bool:
        """401 自动补救流程：先 refresh，再 password login。"""

        # 业务规则：优先使用已有会话做 refresh，失败后才尝试密码登录。
        if _try_auto_refresh_session():
            return True
        if _try_auto_login_password():
            return True
        return False

    def _request_with_auto_reauth(action: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """封装 401 自动补救：失败后最多重试一次原请求。"""

        try:
            return fn()
        except UpstreamRequestError as err:
            if err.http_status != 401:
                raise
            if not _try_auto_reauth():
                raise

            logger.info("401 自动补救完成，重试动作：%s", action)
            return fn()

    # WebSocket 长连接管理器：负责 connect/send/recv/状态维护。
    ws_manager = WsConnectionManager(
        logger=logger,
        ws_base_url=settings.grindr_im_ws_base_url,
        auth_scheme=settings.grindr_auth_scheme,
        token_provider=_resolve_runtime_session_token,
        user_agent=settings.grindr_user_agent,
        device_id=settings.grindr_device_id,
        device_info=settings.grindr_device_info,
        locale=settings.grindr_locale,
        time_zone=settings.grindr_time_zone,
        packet_validator=lambda payload: validate_ws_packet_payload(payload, allow_notify_types=True),
    )

    # ===== profile-manager 路由（保持兼容） =====
    @app.post("/profile/me/get")
    def profile_me_get():
        """获取当前账号资料。"""

        result = _request_with_auto_reauth(
            ACTION_ME_GET,
            lambda: client.get(
                "/v4/me/profile",
                action=ACTION_ME_GET,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
        )
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
        result = _request_with_auto_reauth(
            ACTION_USER_GET,
            lambda: client.get(
                endpoint,
                action=ACTION_USER_GET,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
        )
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

        result = _request_with_auto_reauth(
            ACTION_ME_UPDATE,
            lambda: client.put(
                "/v3.1/me/profile",
                action=ACTION_ME_UPDATE,
                payload=update_payload,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
        )
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

        result = _request_with_auto_reauth(
            ACTION_ME_IMAGES_UPDATE,
            lambda: client.put(
                "/v3/me/profile/images",
                action=ACTION_ME_IMAGES_UPDATE,
                payload=image_payload,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
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
        nearby_query = _prepare_nearby_query(checked, settings.grindr_geohash)

        result = _request_with_auto_reauth(
            ACTION_DISCOVERY_NEARBY_GET,
            lambda: client.get_with_query(
                settings.grindr_discovery_nearby_endpoint,
                action=ACTION_DISCOVERY_NEARBY_GET,
                query=nearby_query,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
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

        result = _request_with_auto_reauth(
            ACTION_DISCOVERY_VIEWED_ME_GET,
            lambda: client.get_with_query(
                settings.grindr_discovery_viewed_me_endpoint,
                action=ACTION_DISCOVERY_VIEWED_ME_GET,
                query=checked,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
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
        result = _request_with_auto_reauth(
            ACTION_DISCOVERY_USER_PROFILE_GET,
            lambda: client.get(
                endpoint,
                action=ACTION_DISCOVERY_USER_PROFILE_GET,
                use_auth=True,
                auth_token=_resolve_runtime_session_token(),
            ),
        )
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

    # ===== chat-manager（WebSocket 长连接） =====
    @app.post("/chat/ws/config/get")
    def chat_ws_config_get():
        """返回 WS 配置与协议能力。"""

        resp = build_success_response(
            ACTION_CHAT_WS_CONFIG_GET,
            data={
                "wsBaseUrl": ws_manager.status().get("wsBaseUrlMasked"),
                "supportedTypes": ws_supported_types(),
                "connection": ws_manager.status(),
            },
            meta={"endpoint": "/chat/ws/config/get"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/connection/status")
    def chat_ws_connection_status():
        """查询当前 WS 长连接状态。"""

        resp = build_success_response(
            ACTION_CHAT_WS_CONNECTION_STATUS,
            data=ws_manager.status(),
            meta={"endpoint": "/chat/ws/connection/status"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/connection/connect")
    def chat_ws_connection_connect():
        """主动建立 WS 长连接。"""

        raw = request.get_json(silent=True)
        payload = _json_or_empty_object(raw, action=ACTION_CHAT_WS_CONNECTION_CONNECT)
        force_reconnect = payload.get("forceReconnect", False)
        if not isinstance(force_reconnect, bool):
            raise ValidationError("INVALID_FORCE_RECONNECT", "forceReconnect 必须是布尔值", http_status=400)

        data = ws_manager.ensure_connected(force_reconnect=force_reconnect)
        resp = build_success_response(
            ACTION_CHAT_WS_CONNECTION_CONNECT,
            data=data,
            meta={"endpoint": "/chat/ws/connection/connect"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/connection/disconnect")
    def chat_ws_connection_disconnect():
        """主动断开 WS 长连接。"""

        data = ws_manager.disconnect(reason="manual_disconnect")
        resp = build_success_response(
            ACTION_CHAT_WS_CONNECTION_DISCONNECT,
            data=data,
            meta={"endpoint": "/chat/ws/connection/disconnect"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/request/preview")
    def chat_ws_request_preview():
        """校验客户端 -> 服务端的 WS 协议包（不发送）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_CHAT_WS_REQUEST_PREVIEW)
        checked = validate_ws_packet_payload(payload, allow_notify_types=False)

        resp = build_success_response(
            ACTION_CHAT_WS_REQUEST_PREVIEW,
            data={
                "valid": True,
                "packet": checked,
                "wsBaseUrl": settings.grindr_im_ws_base_url,
            },
            meta={"endpoint": "/chat/ws/request/preview"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/request/send")
    def chat_ws_request_send():
        """通过长连接发送 WS 协议包。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_CHAT_WS_REQUEST_SEND)
        checked = validate_ws_packet_payload(payload, allow_notify_types=False)
        send_result = ws_manager.send_packet(checked, auto_connect=True)

        resp = build_success_response(
            ACTION_CHAT_WS_REQUEST_SEND,
            data={
                "executed": send_result["sent"],
                "packet": checked,
                "connection": send_result["connection"],
                "requestId": send_result["requestId"],
                "type": send_result["type"],
            },
            meta={"endpoint": "/chat/ws/request/send"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/notify/parse")
    def chat_ws_notify_parse():
        """校验服务端 -> 客户端通知包结构（不做事件持久化）。"""

        raw = request.get_json(silent=True)
        payload = ensure_object(raw, action=ACTION_CHAT_WS_NOTIFY_PARSE)
        checked = validate_ws_packet_payload(payload, allow_notify_types=True)

        resp = build_success_response(
            ACTION_CHAT_WS_NOTIFY_PARSE,
            data={"valid": True, "packet": checked},
            meta={"endpoint": "/chat/ws/notify/parse"},
        )
        return jsonify(resp), HTTPStatus.OK

    @app.post("/chat/ws/notify/pull")
    def chat_ws_notify_pull():
        """拉取接收缓冲中的通知。"""

        raw = request.get_json(silent=True)
        payload = _json_or_empty_object(raw, action=ACTION_CHAT_WS_NOTIFY_PULL)

        limit = payload.get("limit", 20)
        clear = payload.get("clear", True)
        if not isinstance(limit, int):
            raise ValidationError("INVALID_LIMIT", "limit 必须是整数", http_status=400)
        if not isinstance(clear, bool):
            raise ValidationError("INVALID_CLEAR", "clear 必须是布尔值", http_status=400)

        data = ws_manager.pull_notifications(limit=limit, clear=clear)
        resp = build_success_response(
            ACTION_CHAT_WS_NOTIFY_PULL,
            data=data,
            meta={"endpoint": "/chat/ws/notify/pull"},
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

    @app.errorhandler(WsConnectionError)
    def handle_ws_connection_error(err: WsConnectionError):
        """WebSocket 连接错误处理。"""

        payload = build_error_response(
            action="chat.ws.connection",
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
