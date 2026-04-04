"""grindr_adapter 配置加载模块。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    """配置错误：用于在启动阶段给出明确错误信息。"""


@dataclass(frozen=True)
class Settings:
    """运行配置对象。"""

    grindr_base_url: str
    grindr_auth_token: str
    grindr_auth_scheme: str
    grindr_device_id: str
    grindr_device_info: str
    grindr_locale: str
    grindr_time_zone: str
    grindr_user_agent: str
    grindr_auto_login_email: str
    grindr_auto_login_password: str
    grindr_geohash: str
    grindr_timeout_seconds: int
    grindr_retry_times: int
    grindr_log_dir: str
    grindr_session_file: str
    grindr_discovery_nearby_endpoint: str
    grindr_discovery_viewed_me_endpoint: str
    grindr_im_ws_base_url: str
    env_file: str


def _workspace_root() -> Path:
    """推断工作区根目录：.../grindr-traffic。"""

    return Path(__file__).resolve().parent.parent.parent


def _default_env_file() -> Path:
    """返回默认环境文件路径。"""

    return _workspace_root() / ".secrets" / "grindr.env"


def _parse_env_file(path: Path) -> dict[str, str]:
    """读取 .env 文件，支持 KEY=VALUE 形式。"""

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _require_value(values: dict[str, str], key: str) -> str:
    """读取并校验必填配置。"""

    value = values.get(key, "").strip()
    if not value or value == "replace_me":
        raise ConfigError(f"缺少必要配置：{key}（请在 .secrets/grindr.env 中设置）")
    return value


def _optional_value(values: dict[str, str], key: str, default: str = "") -> str:
    """读取可选配置。"""

    value = values.get(key, default).strip()
    if value == "replace_me":
        return default
    return value


def _parse_positive_int(values: dict[str, str], key: str, default: int) -> int:
    """解析正整数配置并校验。"""

    raw = values.get(key, str(default)).strip()
    try:
        number = int(raw)
    except ValueError as exc:
        raise ConfigError(f"配置 {key} 必须是整数，当前值：{raw}") from exc
    if number <= 0:
        raise ConfigError(f"配置 {key} 必须大于 0，当前值：{raw}")
    return number


def _resolve_path(raw_value: str, *, base: Path) -> Path:
    """把相对路径解析为绝对路径。"""

    path = Path(raw_value)
    if path.is_absolute():
        return path
    return (base / raw_value).resolve()


def _normalize_endpoint(raw_value: str, *, default: str) -> str:
    """规范化 endpoint：空值回退默认，且必须以 / 开头。"""

    value = raw_value.strip() or default
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def load_settings() -> Settings:
    """加载运行配置。

    优先级：系统环境变量 > .secrets/grindr.env 文件。
    """

    env_path = Path(os.getenv("GRINDR_ENV_FILE", str(_default_env_file()))).expanduser()
    if not env_path.exists():
        raise ConfigError(f"环境文件不存在：{env_path}")

    file_values = _parse_env_file(env_path)

    merged: dict[str, str] = dict(file_values)
    for key, value in os.environ.items():
        if key.startswith("GRINDR_") and value.strip():
            merged[key] = value.strip()

    base_url = _require_value(merged, "GRINDR_BASE_URL").rstrip("/")
    device_id = _require_value(merged, "GRINDR_DEVICE_ID")
    user_agent = _require_value(merged, "GRINDR_USER_AGENT")
    auth_scheme = _optional_value(merged, "GRINDR_AUTH_SCHEME", default="Bearer") or "Bearer"
    auth_token = _optional_value(merged, "GRINDR_AUTH_TOKEN", default="")
    auto_login_email = _optional_value(merged, "GRINDR_AUTO_LOGIN_EMAIL", default="")
    auto_login_password = _optional_value(merged, "GRINDR_AUTO_LOGIN_PASSWORD", default="")
    geohash = _optional_value(merged, "GRINDR_GEOHASH", default="")
    # L-* 头兼容：未显式配置时回退到 device_id / 常用默认值。
    device_info = _optional_value(merged, "GRINDR_DEVICE_INFO", default=device_id) or device_id
    locale = _optional_value(merged, "GRINDR_LOCALE", default="zh_CN") or "zh_CN"
    time_zone = _optional_value(merged, "GRINDR_TIME_ZONE", default="America/New_York") or "America/New_York"

    timeout_seconds = _parse_positive_int(merged, "GRINDR_TIMEOUT_SECONDS", default=20)
    retry_times = _parse_positive_int(merged, "GRINDR_RETRY_TIMES", default=2)

    log_dir_raw = _optional_value(merged, "GRINDR_LOG_DIR", default="./logs") or "./logs"
    session_file_raw = _optional_value(
        merged,
        "GRINDR_SESSION_FILE",
        default="./.secrets/grindr.session.json",
    )
    if not session_file_raw:
        raise ConfigError("缺少必要配置：GRINDR_SESSION_FILE（请在 .secrets/grindr.env 中设置）")

    workspace = _workspace_root()
    log_dir_path = _resolve_path(log_dir_raw, base=workspace)
    session_file_path = _resolve_path(session_file_raw, base=workspace)
    nearby_endpoint = _normalize_endpoint(
        _optional_value(merged, "GRINDR_DISCOVERY_NEARBY_ENDPOINT", default="/v1/cascade"),
        default="/v1/cascade",
    )
    viewed_me_endpoint = _normalize_endpoint(
        _optional_value(merged, "GRINDR_DISCOVERY_VIEWED_ME_ENDPOINT", default="/v7/views/list"),
        default="/v7/views/list",
    )
    im_ws_base_url = _optional_value(
        merged,
        "GRINDR_IM_WS_BASE_URL",
        default="wss://example.invalid/im",
    ) or "wss://example.invalid/im"

    return Settings(
        grindr_base_url=base_url,
        grindr_auth_token=auth_token,
        grindr_auth_scheme=auth_scheme,
        grindr_device_id=device_id,
        grindr_device_info=device_info,
        grindr_locale=locale,
        grindr_time_zone=time_zone,
        grindr_user_agent=user_agent,
        grindr_auto_login_email=auto_login_email,
        grindr_auto_login_password=auto_login_password,
        grindr_geohash=geohash,
        grindr_timeout_seconds=timeout_seconds,
        grindr_retry_times=retry_times,
        grindr_log_dir=str(log_dir_path),
        grindr_session_file=str(session_file_path),
        grindr_discovery_nearby_endpoint=nearby_endpoint,
        grindr_discovery_viewed_me_endpoint=viewed_me_endpoint,
        grindr_im_ws_base_url=im_ws_base_url,
        env_file=str(env_path),
    )
