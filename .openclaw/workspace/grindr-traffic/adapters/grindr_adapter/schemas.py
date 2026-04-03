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
