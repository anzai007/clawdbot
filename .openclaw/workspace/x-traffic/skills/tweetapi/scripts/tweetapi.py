#!/usr/bin/env python3
"""
TweetAPI 通用调用器（X-API-Key 认证）。

核心逻辑：
1) 从环境变量读取密钥与基础地址。
2) 组装带 X-API-Key 的 HTTP 请求。
3) 支持 dry-run，先验证请求再真实发送。
"""

import argparse
import json
import os
import sys
from urllib import error, parse, request


def build_url(base_url: str, path: str, query: str | None) -> str:
    # 业务逻辑：统一处理 path/query，避免调用方手工拼接出错。
    if not path.startswith("/"):
        path = "/" + path
    url = base_url.rstrip("/") + path
    if query:
        url = url + ("&" if "?" in url else "?") + query
    return url


def send_http(method: str, url: str, api_key: str, body_json: str | None, timeout: int) -> int:
    # 核心认证逻辑：所有请求都注入 X-API-Key 头。
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
    }

    data = None
    if body_json is not None:
        headers["Content-Type"] = "application/json"
        data = body_json.encode("utf-8")

    req = request.Request(url=url, data=data, headers=headers, method=method.upper())

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            print(text)
            return 0
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}", file=sys.stderr)
        print(body, file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Request failed: {e}", file=sys.stderr)
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="TweetAPI caller with X-API-Key")
    sub = parser.add_subparsers(dest="cmd", required=True)

    req = sub.add_parser("request", help="Call any TweetAPI endpoint")
    req.add_argument("method", help="HTTP method, e.g. GET/POST")
    req.add_argument("path", help="Endpoint path from TweetAPI docs, e.g. /v1/tweets")
    req.add_argument("--query", default=None, help="Raw query string, e.g. q=openclaw&limit=10")
    req.add_argument("--json", default=None, help="JSON body string")
    req.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    req.add_argument("--dry-run", action="store_true", help="Print request only, do not send")

    args = parser.parse_args()

    api_key = os.environ.get("TWEETAPI_KEY", "").strip()
    base_url = os.environ.get("TWEETAPI_BASE_URL", "https://api.tweetapi.com").strip()

    if not api_key:
        print("Missing TWEETAPI_KEY", file=sys.stderr)
        return 1

    if args.json is not None:
        try:
            json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"Invalid --json payload: {e}", file=sys.stderr)
            return 1

    url = build_url(base_url, args.path, args.query)

    if args.dry_run:
        preview = {
            "method": args.method.upper(),
            "url": url,
            "headers": {
                "X-API-Key": "***",
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if args.json is not None else {}),
            },
            "json": json.loads(args.json) if args.json is not None else None,
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    return send_http(args.method, url, api_key, args.json, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
