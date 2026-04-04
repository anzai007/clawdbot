"""grindr_adapter WebSocket 长连接管理模块。"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

try:
    import websocket
except ImportError:  # pragma: no cover - 依赖缺失时在运行期明确报错
    websocket = None  # type: ignore[assignment]


_SENSITIVE_QUERY_KEYS = {"token", "authToken", "sessionToken", "authorization"}


class WsConnectionError(RuntimeError):
    """WebSocket 连接管理错误。"""

    def __init__(self, *, code: str, message: str, http_status: int = 500) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now_iso() -> str:
    """返回 UTC ISO 时间戳。"""

    return datetime.now(timezone.utc).isoformat()


def _mask_token(token: str) -> str:
    """脱敏 token：仅保留首尾少量字符。"""

    value = token.strip()
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def _mask_ws_url(raw_url: str) -> str:
    """脱敏 WS URL，避免在响应中泄露 query token。"""

    if not raw_url.strip():
        return raw_url

    parts = urlsplit(raw_url)
    masked_query_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in _SENSITIVE_QUERY_KEYS:
            masked_query_pairs.append((key, _mask_token(value)))
        else:
            masked_query_pairs.append((key, value))
    masked_query = urlencode(masked_query_pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, masked_query, parts.fragment))


class WsConnectionManager:
    """WebSocket 长连接管理器。

    职责：
    - 维护单例长连接（connect / send / disconnect）
    - 后台持续接收通知并放入内存缓冲
    - 提供连接状态与通知读取能力
    """

    def __init__(
        self,
        *,
        logger: logging.Logger,
        ws_base_url: str,
        auth_scheme: str,
        token_provider: Callable[[], str | None],
        user_agent: str,
        device_id: str,
        device_info: str,
        locale: str,
        time_zone: str,
        packet_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        connect_timeout_seconds: int = 8,
        recv_timeout_seconds: int = 30,
        ping_interval_seconds: int = 25,
        max_buffer_size: int = 200,
    ) -> None:
        self._logger = logger
        self._ws_base_url_template = ws_base_url.strip()
        self._auth_scheme = auth_scheme.strip() or "Bearer"
        self._token_provider = token_provider
        self._user_agent = user_agent
        self._device_id = device_id
        self._device_info = device_info
        self._locale = locale
        self._time_zone = time_zone
        self._packet_validator = packet_validator
        self._connect_timeout_seconds = max(1, connect_timeout_seconds)
        self._recv_timeout_seconds = max(2, recv_timeout_seconds)
        self._ping_interval_seconds = max(5, ping_interval_seconds)

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._ws: Any = None
        self._recv_thread: threading.Thread | None = None
        self._notifications: deque[dict[str, Any]] = deque(maxlen=max(10, max_buffer_size))

        self._connected = False
        self._connected_at: str | None = None
        self._last_send_at: str | None = None
        self._last_recv_at: str | None = None
        self._last_error: str | None = None
        self._received_count = 0

    def _resolve_ws_url(self) -> str:
        """解析最终 WS URL，支持 authToken 占位符替换。"""

        url = self._ws_base_url_template
        if not url:
            raise WsConnectionError(
                code="WS_BASE_URL_MISSING",
                message="缺少 GRINDR_IM_WS_BASE_URL 配置",
                http_status=400,
            )

        token = (self._token_provider() or "").strip()
        encoded_token = quote(token, safe="")
        for marker in ("{{authToken}}", "{authToken}", "${authToken}", "__AUTH_TOKEN__"):
            url = url.replace(marker, encoded_token)

        lower = url.lower()
        if not (lower.startswith("ws://") or lower.startswith("wss://")):
            raise WsConnectionError(
                code="WS_BASE_URL_INVALID",
                message="GRINDR_IM_WS_BASE_URL 必须以 ws:// 或 wss:// 开头",
                http_status=400,
            )
        return url

    def _build_headers(self) -> list[str]:
        """构建 WS 握手头，兼容 Grindr 常用头部。"""

        headers = [
            f"User-Agent: {self._user_agent}",
            f"X-Device-Id: {self._device_id}",
            f"L-Device-Info: {self._device_info}",
            f"L-Locale: {self._locale}",
            f"L-Time-Zone: {self._time_zone}",
            "Accept: application/json",
        ]

        token = (self._token_provider() or "").strip()
        if token:
            headers.append(f"Authorization: {self._auth_scheme} {token}")
        return headers

    def _set_disconnected_locked(self, error_message: str | None = None) -> None:
        """在持锁上下文中更新断开状态。"""

        self._connected = False
        self._connected_at = None
        if error_message:
            self._last_error = error_message

        ws = self._ws
        self._ws = None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def ensure_connected(self, *, force_reconnect: bool = False) -> dict[str, Any]:
        """确保长连接可用；已连接时复用。"""

        if websocket is None:
            raise WsConnectionError(
                code="WS_DEP_MISSING",
                message="缺少 websocket-client 依赖，请先安装 requirements",
                http_status=500,
            )

        with self._lock:
            if force_reconnect:
                self._disconnect_locked(reason="force_reconnect")

            if self._connected and self._ws is not None:
                return self.status()

            ws_url = self._resolve_ws_url()
            headers = self._build_headers()

            self._stop_event.clear()
            try:
                ws = websocket.create_connection(
                    ws_url,
                    timeout=self._connect_timeout_seconds,
                    header=headers,
                    enable_multithread=True,
                )
                ws.settimeout(self._recv_timeout_seconds)
            except Exception as exc:
                self._last_error = str(exc)
                raise WsConnectionError(
                    code="WS_CONNECT_FAILED",
                    message=f"WebSocket 建连失败：{exc}",
                    http_status=502,
                ) from exc

            self._ws = ws
            self._connected = True
            self._connected_at = _now_iso()
            self._last_error = None

            self._recv_thread = threading.Thread(
                target=self._recv_loop,
                name="grindr-ws-recv",
                daemon=True,
            )
            self._recv_thread.start()

            # 日志只记录脱敏 URL，避免 query token 泄露。
            self._logger.info("WS 已连接：%s", _mask_ws_url(ws_url))
            return self.status()

    def _recv_loop(self) -> None:
        """后台收包循环：持续拉取并缓存通知。"""

        last_ping_ts = time.time()
        while not self._stop_event.is_set():
            with self._lock:
                ws = self._ws
            if ws is None:
                return

            try:
                message = ws.recv()
                if message is None:
                    raise WsConnectionError(code="WS_RECV_CLOSED", message="连接已关闭", http_status=502)

                notification = self._normalize_notification(message)
                with self._lock:
                    self._notifications.append(notification)
                    self._last_recv_at = _now_iso()
                    self._received_count += 1

            except Exception as exc:
                # 超时不是错误，用于定时发 ping 保活。
                timeout_exc = getattr(websocket, "WebSocketTimeoutException", None)
                if timeout_exc is not None and isinstance(exc, timeout_exc):
                    now_ts = time.time()
                    if now_ts - last_ping_ts >= self._ping_interval_seconds:
                        try:
                            ws.ping()
                            last_ping_ts = now_ts
                        except Exception as ping_exc:
                            with self._lock:
                                self._set_disconnected_locked(str(ping_exc))
                            self._logger.warning("WS ping 失败，连接已断开：%s", ping_exc)
                            return
                    continue

                with self._lock:
                    self._set_disconnected_locked(str(exc))
                self._logger.warning("WS 接收循环异常，连接已断开：%s", exc)
                return

    def _normalize_notification(self, raw_message: Any) -> dict[str, Any]:
        """归一化 WS 收到的通知数据。"""

        record: dict[str, Any] = {
            "receivedAt": _now_iso(),
            "raw": raw_message,
            "valid": False,
        }

        if not isinstance(raw_message, str):
            return record

        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            record["parseError"] = "INVALID_JSON"
            return record

        record["payload"] = payload
        if not isinstance(payload, dict):
            record["parseError"] = "INVALID_PACKET_TYPE"
            return record

        if self._packet_validator is None:
            record["valid"] = True
            return record

        try:
            checked = self._packet_validator(payload)
        except Exception as exc:
            record["parseError"] = str(exc)
            return record

        record["valid"] = True
        record["payload"] = checked
        return record

    def send_packet(self, packet: dict[str, Any], *, auto_connect: bool = True) -> dict[str, Any]:
        """发送协议包到 WS 服务端。"""

        if auto_connect:
            self.ensure_connected(force_reconnect=False)

        with self._lock:
            if not self._connected or self._ws is None:
                raise WsConnectionError(
                    code="WS_NOT_CONNECTED",
                    message="WebSocket 未连接，请先连接后再发送",
                    http_status=409,
                )

            ws = self._ws

        encoded = json.dumps(packet, ensure_ascii=False)
        try:
            ws.send(encoded)
        except Exception as exc:
            with self._lock:
                self._set_disconnected_locked(str(exc))
            raise WsConnectionError(
                code="WS_SEND_FAILED",
                message=f"WebSocket 发送失败：{exc}",
                http_status=502,
            ) from exc

        with self._lock:
            self._last_send_at = _now_iso()

        return {
            "sent": True,
            "requestId": packet.get("requestId"),
            "type": packet.get("type"),
            "connection": self.status(),
        }

    def _disconnect_locked(self, *, reason: str) -> None:
        """持锁断开连接并停止后台线程。"""

        self._stop_event.set()
        ws = self._ws
        self._ws = None
        self._connected = False
        self._connected_at = None
        self._last_error = reason

        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def disconnect(self, *, reason: str = "manual") -> dict[str, Any]:
        """主动断开长连接。"""

        with self._lock:
            self._disconnect_locked(reason=reason)
            return self.status()

    def pull_notifications(self, *, limit: int = 20, clear: bool = True) -> dict[str, Any]:
        """读取内存中的通知缓冲。"""

        if limit <= 0:
            raise WsConnectionError(code="INVALID_LIMIT", message="limit 必须大于 0", http_status=400)

        with self._lock:
            total = len(self._notifications)
            items = list(self._notifications)[-limit:]
            if clear:
                self._notifications.clear()

        return {
            "items": items,
            "count": len(items),
            "bufferedBeforePull": total,
            "cleared": clear,
        }

    def status(self) -> dict[str, Any]:
        """返回连接状态（脱敏）。"""

        with self._lock:
            return {
                "connected": self._connected and self._ws is not None,
                "wsBaseUrlMasked": _mask_ws_url(self._resolve_ws_url()),
                "connectedAt": self._connected_at,
                "lastSendAt": self._last_send_at,
                "lastRecvAt": self._last_recv_at,
                "lastError": self._last_error,
                "receivedCount": self._received_count,
                "bufferedNotifications": len(self._notifications),
                "mode": "live",
            }
