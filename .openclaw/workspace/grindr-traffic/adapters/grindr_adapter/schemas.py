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
    """校验图片更新 payload。

    至少包含 primaryImageHash 或 secondaryImageHashes。
    """

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


def validate_login_password_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验账号密码登录 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "登录 payload 不能为空", http_status=400)

    principal = payload.get("username") or payload.get("email") or payload.get("phone")
    password = payload.get("password")

    if not isinstance(principal, str) or not principal.strip():
        raise ValidationError("INVALID_LOGIN_PRINCIPAL", "username/email/phone 至少提供一个", http_status=400)
    if not isinstance(password, str) or not password.strip():
        raise ValidationError("INVALID_PASSWORD", "password 必填且必须是字符串", http_status=400)

    return payload


def validate_login_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验第三方登录 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "第三方登录 payload 不能为空", http_status=400)

    vendor = payload.get("thirdPartyVendor")
    has_credential = any(payload.get(k) for k in ("idToken", "accessToken", "authCode"))
    if not isinstance(vendor, str) or not vendor.strip():
        raise ValidationError("INVALID_VENDOR", "thirdPartyVendor 必填", http_status=400)
    if not has_credential:
        raise ValidationError("INVALID_THIRDPARTY_TOKEN", "idToken/accessToken/authCode 至少提供一个", http_status=400)

    return payload


def validate_refresh_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验会话刷新 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "刷新 payload 不能为空", http_status=400)

    has_token = any(payload.get(k) for k in ("sessionToken", "refreshToken", "authToken"))
    if not has_token:
        raise ValidationError("INVALID_REFRESH_TOKEN", "sessionToken/refreshToken/authToken 至少提供一个", http_status=400)

    return payload


def validate_refresh_thirdparty_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验第三方会话刷新 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "第三方刷新 payload 不能为空", http_status=400)

    vendor = payload.get("thirdPartyVendor")
    if not isinstance(vendor, str) or not vendor.strip():
        raise ValidationError("INVALID_VENDOR", "thirdPartyVendor 必填", http_status=400)
    if not any(payload.get(k) for k in ("refreshToken", "accessToken", "idToken")):
        raise ValidationError("INVALID_THIRDPARTY_TOKEN", "refreshToken/accessToken/idToken 至少提供一个", http_status=400)

    return payload


def validate_save_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验会话保存 payload。"""

    if not payload:
        raise ValidationError("EMPTY_PAYLOAD", "保存会话 payload 不能为空", http_status=400)

    allowed = {"authToken", "sessionToken", "thirdPartyUserId", "thirdPartyVendor", "source"}
    has_core = any(payload.get(k) for k in ("authToken", "sessionToken", "thirdPartyUserId"))
    if not has_core:
        raise ValidationError("INVALID_SESSION_PAYLOAD", "authToken/sessionToken/thirdPartyUserId 至少提供一个", http_status=400)

    normalized = {k: v for k, v in payload.items() if k in allowed}
    if not normalized:
        raise ValidationError("INVALID_SESSION_PAYLOAD", "没有可保存的会话字段", http_status=400)
    return normalized


def build_session_preview_result(payload: dict[str, Any]) -> dict[str, Any]:
    """构造会话预览结果。"""

    return build_preview_result(payload)
