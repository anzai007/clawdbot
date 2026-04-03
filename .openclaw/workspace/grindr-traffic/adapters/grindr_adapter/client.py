"""grindr_adapter 上游请求客户端。"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from config import Settings
from logger import log_action_event


class UpstreamRequestError(RuntimeError):
    """上游请求错误。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        endpoint: str,
        http_status: int,
        retry_count: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.endpoint = endpoint
        self.http_status = http_status
        self.retry_count = retry_count


class GrindrClient:
    """Grindr 上游调用客户端。

    统一处理 headers、超时、重试与错误转换。
    """

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        """统一组装请求头。"""

        return {
            "Authorization": f"Bearer {self.settings.grindr_auth_token}",
            "User-Agent": self.settings.grindr_user_agent,
            "X-Device-Id": self.settings.grindr_device_id,
            "Accept": "application/json",
        }

    def get(self, endpoint: str, *, action: str) -> dict[str, Any]:
        """执行 GET 请求。"""

        return self._request("GET", endpoint, action=action, payload=None)

    def put(self, endpoint: str, *, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """执行 PUT 请求。"""

        return self._request("PUT", endpoint, action=action, payload=payload)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        action: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """统一请求处理。

        重试策略：
        - 仅对 timeout / connection error / 5xx 重试
        - 不对 4xx 重试
        """

        url = f"{self.settings.grindr_base_url}{endpoint}"
        max_attempts = self.settings.grindr_retry_times + 1

        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            retry_count = attempt - 1
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.settings.grindr_timeout_seconds,
                )

                if 200 <= resp.status_code < 300:
                    data = _safe_json(resp)
                    log_action_event(
                        self.logger,
                        action=action,
                        endpoint=endpoint,
                        success=True,
                        http_status=resp.status_code,
                        retry_count=retry_count,
                        error_code=None,
                    )
                    return {
                        "httpStatus": resp.status_code,
                        "retryCount": retry_count,
                        "endpoint": endpoint,
                        "body": data,
                    }

                if 500 <= resp.status_code < 600 and attempt < max_attempts:
                    continue

                # 4xx 或最终 5xx：直接失败
                error_code = f"HTTP_{resp.status_code}"
                message = _safe_error_message(resp)
                log_action_event(
                    self.logger,
                    action=action,
                    endpoint=endpoint,
                    success=False,
                    http_status=resp.status_code,
                    retry_count=retry_count,
                    error_code=error_code,
                )
                raise UpstreamRequestError(
                    code=error_code,
                    message=message,
                    endpoint=endpoint,
                    http_status=resp.status_code,
                    retry_count=retry_count,
                )

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < max_attempts:
                    continue

                error_code = "NETWORK_TIMEOUT" if isinstance(exc, requests.Timeout) else "NETWORK_CONNECTION"
                log_action_event(
                    self.logger,
                    action=action,
                    endpoint=endpoint,
                    success=False,
                    http_status=503,
                    retry_count=retry_count,
                    error_code=error_code,
                )
                raise UpstreamRequestError(
                    code=error_code,
                    message="上游网络请求失败",
                    endpoint=endpoint,
                    http_status=503,
                    retry_count=retry_count,
                ) from exc

        # 理论上不会走到这里，防御性兜底
        raise UpstreamRequestError(
            code="UNKNOWN_UPSTREAM_ERROR",
            message=str(last_error) if last_error else "未知上游错误",
            endpoint=endpoint,
            http_status=500,
            retry_count=self.settings.grindr_retry_times,
        )


def _safe_json(resp: requests.Response) -> Any:
    """安全解析 JSON，失败时返回文本。"""

    try:
        return resp.json()
    except json.JSONDecodeError:
        return {"raw": resp.text}


def _safe_error_message(resp: requests.Response) -> str:
    """提取错误信息，不暴露敏感信息。"""

    body = _safe_json(resp)
    if isinstance(body, dict):
        for key in ("message", "error", "detail"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"上游请求失败，HTTP {resp.status_code}"
