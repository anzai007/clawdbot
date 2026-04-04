"""grindr_adapter 轻量输入校验模块。"""

from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    """输入校验错误。"""

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def ensure_object(payload: Any, *, action: str) -> dict[str, Any]:
    """确保请求体是 JSON 对象。"""

    if payload is None:
        raise ValidationError("INVALID_JSON", f"{action} 请求体不能为空", http_status=400)
    if not isinstance(payload, dict):
        raise ValidationError("INVALID_JSON", f"{action} 请求体必须是 JSON 对象", http_status=400)
    return payload


def _require_non_empty_string(payload: dict[str, Any], key: str, code: str, message: str) -> str:
    """读取并校验必填字符串。"""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(code, message, http_status=400)
    return value.strip()


# ===== chat-manager（WebSocket 协议）相关校验 =====
WS_CLIENT_TO_SERVER_TYPES = {
    "userConnect",
    "userDisconnect",
    "userList",
    "messageSend",
    "messageReaded",
    "messageRecall",
    "messageDelete",
    "grindrChatSendMedia",
}

WS_SERVER_TO_CLIENT_TYPES = {
    "userUpdateNotify",
    "messageSendedNotify",
    "messageRecvNotify",
    "messageReadedNotify",
    "messageRecallNotify",
    "messageDeleteNotify",
}

WS_ALL_TYPES = WS_CLIENT_TO_SERVER_TYPES | WS_SERVER_TO_CLIENT_TYPES


def ws_supported_types() -> list[str]:
    """返回协议支持的消息类型列表（排序后，便于前端/脚本展示）。"""

    return sorted(WS_ALL_TYPES)


def _validate_packet_data_is_list(payload: dict[str, Any], *, action: str) -> list[dict[str, Any]]:
    """校验 data 为对象数组，并统一返回可变字典列表。"""

    data = payload.get("data")
    if not isinstance(data, list):
        raise ValidationError("INVALID_DATA", f"{action} 的 data 必须是数组", http_status=400)

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError("INVALID_DATA", f"{action} 的 data[{idx}] 必须是对象", http_status=400)
        normalized.append(dict(item))
    return normalized


def _validate_message_send_item(item: dict[str, Any], *, idx: int) -> None:
    """校验 messageSend 的单条消息结构。"""

    required_strings = (
        ("messageId", "INVALID_MESSAGE_ID", "messageId 必填且必须是字符串"),
        ("conversationId", "INVALID_CONVERSATION_ID", "conversationId 必填且必须是字符串"),
        ("sender", "INVALID_SENDER", "sender 必填且必须是字符串"),
        ("senderTime", "INVALID_SENDER_TIME", "senderTime 必填且必须是字符串"),
        ("target", "INVALID_TARGET", "target 必填且必须是字符串"),
    )
    for key, code, message in required_strings:
        _require_non_empty_string(item, key, code, f"messageSend.data[{idx}] {message}")

    message_type = _require_non_empty_string(
        item,
        "messageType",
        "INVALID_MESSAGE_TYPE",
        f"messageSend.data[{idx}] messageType 必填且必须是字符串",
    )
    if message_type not in {"text", "image"}:
        raise ValidationError(
            "INVALID_MESSAGE_TYPE",
            f"messageSend.data[{idx}] messageType 仅支持 text/image",
            http_status=400,
        )

    if "messageContent" not in item:
        raise ValidationError("INVALID_MESSAGE_CONTENT", f"messageSend.data[{idx}] messageContent 必填", http_status=400)
    message_content = item.get("messageContent")
    if message_type == "text":
        if not isinstance(message_content, str) or not message_content.strip():
            raise ValidationError(
                "INVALID_MESSAGE_CONTENT",
                f"messageSend.data[{idx}] 文本消息 messageContent 必须是非空字符串",
                http_status=400,
            )
    else:
        if not isinstance(message_content, dict):
            raise ValidationError(
                "INVALID_MESSAGE_CONTENT",
                f"messageSend.data[{idx}] 图片消息 messageContent 必须是对象",
                http_status=400,
            )
        url = message_content.get("url")
        width = message_content.get("width")
        height = message_content.get("height")
        if not isinstance(url, str) or not url.strip():
            raise ValidationError(
                "INVALID_MESSAGE_CONTENT",
                f"messageSend.data[{idx}] 图片消息 url 必填且必须是字符串",
                http_status=400,
            )
        if not isinstance(width, (int, float)) or width <= 0:
            raise ValidationError(
                "INVALID_MESSAGE_CONTENT",
                f"messageSend.data[{idx}] 图片消息 width 必须大于 0",
                http_status=400,
            )
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValidationError(
                "INVALID_MESSAGE_CONTENT",
                f"messageSend.data[{idx}] 图片消息 height 必须大于 0",
                http_status=400,
            )


def _validate_message_readed_item(item: dict[str, Any], *, idx: int) -> None:
    """校验 messageReaded 单条结构。"""

    _require_non_empty_string(item, "conversationId", "INVALID_CONVERSATION_ID", f"messageReaded.data[{idx}] conversationId 必填")
    _require_non_empty_string(item, "user", "INVALID_USER", f"messageReaded.data[{idx}] user 必填")
    _require_non_empty_string(item, "messageTime", "INVALID_MESSAGE_TIME", f"messageReaded.data[{idx}] messageTime 必填")


def _validate_message_recall_or_delete_item(item: dict[str, Any], *, idx: int, message_type: str) -> None:
    """校验 messageRecall / messageDelete 单条结构。"""

    _require_non_empty_string(item, "user", "INVALID_USER", f"{message_type}.data[{idx}] user 必填")
    _require_non_empty_string(item, "messageId", "INVALID_MESSAGE_ID", f"{message_type}.data[{idx}] messageId 必填")


def _validate_message_notify_item(item: dict[str, Any], *, idx: int, message_type: str) -> None:
    """校验撤回/删除通知结构。"""

    _require_non_empty_string(item, "messageId", "INVALID_MESSAGE_ID", f"{message_type}.data[{idx}] messageId 必填")


def _validate_grindr_send_media_item(item: dict[str, Any], *, idx: int) -> None:
    """校验 grindrChatSendMedia 单条结构。"""

    _require_non_empty_string(item, "sender", "INVALID_SENDER", f"grindrChatSendMedia.data[{idx}] sender 必填")
    _require_non_empty_string(item, "target", "INVALID_TARGET", f"grindrChatSendMedia.data[{idx}] target 必填")

    created_at = item.get("createdAt")
    media_id = item.get("mediaId")
    if not isinstance(created_at, int) or created_at <= 0:
        raise ValidationError(
            "INVALID_CREATED_AT",
            f"grindrChatSendMedia.data[{idx}] createdAt 必须是正整数（13位毫秒时间戳）",
            http_status=400,
        )
    if not isinstance(media_id, int) or media_id <= 0:
        raise ValidationError(
            "INVALID_MEDIA_ID",
            f"grindrChatSendMedia.data[{idx}] mediaId 必须是正整数",
            http_status=400,
        )

    for field in ("expiring", "takenOnGrindr"):
        value = item.get(field)
        if not isinstance(value, bool):
            raise ValidationError(
                "INVALID_BOOLEAN_FIELD",
                f"grindrChatSendMedia.data[{idx}] {field} 必须是布尔值",
                http_status=400,
            )


def validate_ws_packet_payload(payload: dict[str, Any], *, allow_notify_types: bool = True) -> dict[str, Any]:
    """校验 WebSocket 协议包结构（骨架阶段只做格式校验，不发起真实 WS 请求）。"""

    request_id = payload.get("requestId")
    if not isinstance(request_id, int) or request_id <= 0:
        raise ValidationError("INVALID_REQUEST_ID", "requestId 必须是大于 0 的整数", http_status=400)

    source = payload.get("source", "")
    if source is None:
        source = ""
    if not isinstance(source, str):
        raise ValidationError("INVALID_SOURCE", "source 必须是字符串", http_status=400)

    message_type = payload.get("type")
    if not isinstance(message_type, str) or not message_type.strip():
        raise ValidationError("INVALID_TYPE", "type 必填且必须是字符串", http_status=400)
    message_type = message_type.strip()

    allowed_types = set(WS_CLIENT_TO_SERVER_TYPES)
    if allow_notify_types:
        allowed_types |= WS_SERVER_TO_CLIENT_TYPES
    if message_type not in allowed_types:
        raise ValidationError("UNSUPPORTED_TYPE", f"不支持的消息类型：{message_type}", http_status=400)

    data = _validate_packet_data_is_list(payload, action=message_type)

    # 类型分支校验：仅检查必要字段，不做业务调用。
    if message_type in {"userConnect", "userDisconnect"}:
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _require_non_empty_string(item, "user", "INVALID_USER", f"{message_type}.data[{idx}] user 必填")
    elif message_type == "userList":
        # userList 请求允许空数组，服务端响应也会返回数组。
        pass
    elif message_type in {"messageSend", "messageSendedNotify", "messageRecvNotify"}:
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_message_send_item(item, idx=idx)
    elif message_type in {"messageReaded", "messageReadedNotify"}:
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_message_readed_item(item, idx=idx)
    elif message_type == "messageRecall":
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_message_recall_or_delete_item(item, idx=idx, message_type=message_type)
    elif message_type == "messageDelete":
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_message_recall_or_delete_item(item, idx=idx, message_type=message_type)
    elif message_type in {"messageRecallNotify", "messageDeleteNotify"}:
        if not data:
            raise ValidationError("INVALID_DATA", f"{message_type} 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_message_notify_item(item, idx=idx, message_type=message_type)
    elif message_type == "grindrChatSendMedia":
        if not data:
            raise ValidationError("INVALID_DATA", "grindrChatSendMedia 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _validate_grindr_send_media_item(item, idx=idx)
    elif message_type == "userUpdateNotify":
        if not data:
            raise ValidationError("INVALID_DATA", "userUpdateNotify 的 data 至少包含 1 项", http_status=400)
        for idx, item in enumerate(data):
            _require_non_empty_string(item, "user", "INVALID_USER", f"userUpdateNotify.data[{idx}] user 必填")
            status = item.get("status")
            if not isinstance(status, int):
                raise ValidationError("INVALID_STATUS", f"userUpdateNotify.data[{idx}] status 必须是整数", http_status=400)

    normalized: dict[str, Any] = {
        "requestId": request_id,
        "source": source,
        "type": message_type,
        "data": data,
    }
    if "errors" in payload:
        errors = payload.get("errors")
        if errors is not None and not isinstance(errors, dict):
            raise ValidationError("INVALID_ERRORS", "errors 字段必须是对象", http_status=400)
        normalized["errors"] = errors or {}

    return normalized


# ===== profile-manager 相关校验（保持兼容） =====
def validate_profile_id_payload(payload: dict[str, Any]) -> int:
    """校验 profileId。"""

    if "profileId" not in payload:
        raise ValidationError("MISSING_PROFILE_ID", "字段 profileId 必填", http_status=400)

    profile_id = payload["profileId"]
    if not isinstance(profile_id, int):
        raise ValidationError("INVALID_PROFILE_ID", "profileId 必须是整数", http_status=400)
    if profile_id <= 0:
        raise ValidationError("INVALID_PROFILE_ID", "profileId 必须大于 0", http_status=400)

    return profile_id


def validate_discovery_list_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验发现页列表查询参数。

    当前最小规则：
    - `limit` 可选，必须是 1~200 的整数
    - `cursor` 可选，必须是非空字符串
    - 其他字段先透传，留给上游按需处理
    """

    if not payload:
        return {}

    normalized = dict(payload)

    if "limit" in normalized:
        limit = normalized["limit"]
        if not isinstance(limit, int):
            raise ValidationError("INVALID_LIMIT", "limit 必须是整数", http_status=400)
        if limit <= 0 or limit > 200:
            raise ValidationError("INVALID_LIMIT", "limit 必须在 1~200 之间", http_status=400)

    if "cursor" in normalized:
        cursor = normalized["cursor"]
        if not isinstance(cursor, str) or not cursor.strip():
            raise ValidationError("INVALID_CURSOR", "cursor 必须是非空字符串", http_status=400)
        normalized["cursor"] = cursor.strip()

    return normalized


def validate_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验资料更新 payload 不能为空。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "资料更新 payload 不能为空", http_status=400)
    return payload


def validate_images_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验图片更新 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "图片更新 payload 不能为空", http_status=400)

    has_primary = bool(payload.get("primaryImageHash"))
    has_secondary = "secondaryImageHashes" in payload and bool(payload.get("secondaryImageHashes"))

    if not (has_primary or has_secondary):
        raise ValidationError(
            "INVALID_IMAGE_PAYLOAD",
            "图片更新 payload 至少包含 primaryImageHash 或 secondaryImageHashes",
            http_status=400,
        )

    secondary_hashes = payload.get("secondaryImageHashes")
    if secondary_hashes is not None and not isinstance(secondary_hashes, list):
        raise ValidationError("INVALID_IMAGE_PAYLOAD", "secondaryImageHashes 必须是数组", http_status=400)

    return payload


# ===== session-auth 相关校验 =====
def validate_auth_login_password_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验密码登录输入。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "登录 payload 不能为空", http_status=400)

    email = _require_non_empty_string(payload, "email", "INVALID_EMAIL", "email 必填且必须是字符串")
    password = _require_non_empty_string(payload, "password", "INVALID_PASSWORD", "password 必填且必须是字符串")

    result: dict[str, Any] = {
        "email": email,
        "password": password,
    }

    token = payload.get("token")
    if token is not None:
        if not isinstance(token, str):
            raise ValidationError("INVALID_TOKEN", "token 必须是字符串", http_status=400)
        result["token"] = token

    geohash = payload.get("geohash")
    if geohash is not None:
        if not isinstance(geohash, str):
            raise ValidationError("INVALID_GEOHASH", "geohash 必须是字符串", http_status=400)
        result["geohash"] = geohash

    return result


def validate_auth_login_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验第三方登录输入。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "第三方登录 payload 不能为空", http_status=400)

    vendor = payload.get("thirdPartyVendor")
    if isinstance(vendor, int):
        if vendor <= 0:
            raise ValidationError("INVALID_VENDOR", "thirdPartyVendor 必须大于 0", http_status=400)
    elif isinstance(vendor, str):
        if not vendor.strip():
            raise ValidationError("INVALID_VENDOR", "thirdPartyVendor 必填", http_status=400)
    else:
        raise ValidationError("INVALID_VENDOR", "thirdPartyVendor 必填", http_status=400)

    token = _require_non_empty_string(
        payload,
        "thirdPartyToken",
        "INVALID_THIRDPARTY_TOKEN",
        "thirdPartyToken 必填且必须是字符串",
    )

    result: dict[str, Any] = {
        "thirdPartyVendor": vendor,
        "thirdPartyToken": token,
    }

    geohash = payload.get("geohash")
    if geohash is not None:
        if not isinstance(geohash, str):
            raise ValidationError("INVALID_GEOHASH", "geohash 必须是字符串", http_status=400)
        result["geohash"] = geohash

    return result


def validate_auth_refresh_session_payload(
    payload: dict[str, Any],
    *,
    has_local_auth_token: bool,
) -> dict[str, Any]:
    """校验会话刷新输入。

    规则：payload 中至少有 authToken，或本地已有 session 的 authToken。
    """

    if not payload:
        payload = {}

    auth_token = payload.get("authToken")
    if auth_token is not None and (not isinstance(auth_token, str) or not auth_token.strip()):
        raise ValidationError("INVALID_AUTH_TOKEN", "authToken 必须是非空字符串", http_status=400)

    if not auth_token and not has_local_auth_token:
        raise ValidationError(
            "MISSING_AUTH_TOKEN",
            "refresh_session 至少需要 authToken 或本地已有 session.authToken",
            http_status=400,
        )

    result: dict[str, Any] = {}
    if isinstance(auth_token, str) and auth_token.strip():
        result["authToken"] = auth_token.strip()

    for key, code in (("token", "INVALID_TOKEN"), ("email", "INVALID_EMAIL"), ("geohash", "INVALID_GEOHASH")):
        value = payload.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValidationError(code, f"{key} 必须是字符串", http_status=400)
        result[key] = value

    return result


def validate_auth_refresh_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验第三方会话刷新输入。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "第三方刷新 payload 不能为空", http_status=400)

    auth_token = _require_non_empty_string(payload, "authToken", "INVALID_AUTH_TOKEN", "authToken 必填")
    third_party_user_id = _require_non_empty_string(
        payload,
        "thirdPartyUserId",
        "INVALID_THIRDPARTY_USER_ID",
        "thirdPartyUserId 必填",
    )

    result: dict[str, Any] = {
        "authToken": auth_token,
        "thirdPartyUserId": third_party_user_id,
    }

    geohash = payload.get("geohash")
    if geohash is not None:
        if not isinstance(geohash, str):
            raise ValidationError("INVALID_GEOHASH", "geohash 必须是字符串", http_status=400)
        result["geohash"] = geohash

    return result


def validate_auth_session_save_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验会话保存输入。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "会话保存 payload 不能为空", http_status=400)

    allowed = {"authToken", "sessionToken", "thirdPartyUserId", "thirdPartyVendor", "email", "token", "source"}
    normalized = {k: v for k, v in payload.items() if k in allowed and v is not None}

    has_any = any(normalized.get(k) for k in ("authToken", "sessionToken", "thirdPartyUserId"))
    if not has_any:
        raise ValidationError(
            "INVALID_SESSION_PAYLOAD",
            "authToken/sessionToken/thirdPartyUserId 至少提供一个",
            http_status=400,
        )

    return normalized


def build_preview_result(payload: dict[str, Any]) -> dict[str, Any]:
    """构造预览结果。

    preview 路由只做输入校验和摘要，不访问上游。
    """

    changed_fields = sorted(payload.keys())
    payload_summary: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, list):
            payload_summary[key] = {"type": "list", "size": len(value)}
        elif isinstance(value, dict):
            payload_summary[key] = {"type": "object", "size": len(value)}
        else:
            payload_summary[key] = {"type": type(value).__name__}

    return {
        "changedFields": changed_fields,
        "payloadSummary": payload_summary,
        "valid": True,
    }


# 兼容旧函数名，避免已有调用方中断。
def validate_login_password_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：转发到 session-auth 密码登录校验。"""

    return validate_auth_login_password_payload(payload)


def validate_login_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：转发到 session-auth 三方登录校验。"""

    return validate_auth_login_thirdparty_payload(payload)


def validate_refresh_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：在未知本地态下仍要求 payload 中给 authToken。"""

    return validate_auth_refresh_session_payload(payload, has_local_auth_token=False)


def validate_refresh_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：转发到 session-auth 三方刷新校验。"""

    return validate_auth_refresh_thirdparty_payload(payload)


def validate_save_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：转发到 session-auth 会话保存校验。"""

    return validate_auth_session_save_payload(payload)


def build_session_preview_result(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容旧名：session preview 使用统一摘要结构。"""

    return build_preview_result(payload)
