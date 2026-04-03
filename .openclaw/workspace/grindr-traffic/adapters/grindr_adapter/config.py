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
    grindr_device_id: str
    grindr_user_agent: str
    grindr_timeout_seconds: int
    grindr_retry_times: int
    grindr_log_dir: str
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


def load_settings() -> Settings:
    """加载运行配置。

    优先级：系统环境变量 > .secrets/grindr.env 文件。
    """

    env_path = Path(os.getenv("GRINDR_ENV_FILE", str(_default_env_file()))).expanduser()
    if not env_path.exists():
        raise ConfigError(f"环境文件不存在：{env_path}")

    file_values = _parse_env_file(env_path)

    merged: dict[str, str] = dict(file_values)
    for key in file_values:
        if key in os.environ and os.environ[key].strip():
            merged[key] = os.environ[key].strip()

    base_url = _require_value(merged, "GRINDR_BASE_URL").rstrip("/")
    auth_token = _require_value(merged, "GRINDR_AUTH_TOKEN")
    device_id = _require_value(merged, "GRINDR_DEVICE_ID")
    user_agent = _require_value(merged, "GRINDR_USER_AGENT")
    timeout_seconds = _parse_positive_int(merged, "GRINDR_TIMEOUT_SECONDS", default=20)
    retry_times = _parse_positive_int(merged, "GRINDR_RETRY_TIMES", default=2)

    log_dir = merged.get("GRINDR_LOG_DIR", "./logs").strip() or "./logs"
    log_dir_path = (env_path.parent / log_dir).resolve() if not Path(log_dir).is_absolute() else Path(log_dir)

    return Settings(
        grindr_base_url=base_url,
        grindr_auth_token=auth_token,
        grindr_device_id=device_id,
        grindr_user_agent=user_agent,
        grindr_timeout_seconds=timeout_seconds,
        grindr_retry_times=retry_times,
        grindr_log_dir=str(log_dir_path),
        env_file=str(env_path),
    )
