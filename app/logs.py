"""Lightweight log sender that posts to an external service and prints locally.

Environment variables (loaded from .env via app.config):
    LOG_ENDPOINT (필수): 로그를 전송할 HTTP 엔드포인트(URL).
    LOG_SOURCE (선택): 로그 발생 소스 식별자. 기본값 "final-py".
    LOG_TIMEOUT (선택): 요청 타임아웃(초). 기본 5.0.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from app import config

class LogSendError(RuntimeError):
    """Raised when a log cannot be delivered to the remote endpoint."""


def send_log(
    *,
    message: str,
    level: str = "INFO",
    meta: Optional[Dict[str, Any]] = None,
    endpoint: Optional[str] = None,
    source: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.Client] = None,
) -> httpx.Response:
    """외부 로그 수집기로 전송하고 콘솔에도 출력한다.

    Args:
        message: 전송할 메시지.
        level: 로그 레벨 문자열. 기본 "INFO".
        meta: 추가 데이터(dict). 기본 빈 dict.
        endpoint: 명시적 엔드포인트. 없으면 LOG_ENDPOINT 사용.
        source: 로그 발생 소스 식별자. 기본 LOG_SOURCE 또는 "final-py".
        timeout: 요청 타임아웃(초). 없으면 LOG_TIMEOUT 또는 5.0초.
        client: 재사용할 httpx.Client. 없으면 내부에서 생성 후 닫는다.
    """

    meta = meta or {}
    payload = {
        "message": message,
        "level": level,
        "meta": meta,
        "source": config.get_log_source(source),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 즉시 로컬 콘솔 확인
    print(f"[LOG][{payload['level']}] {payload['message']} | meta={payload['meta']}")

    endpoint_url = config.get_log_endpoint(endpoint)
    timeout_val = config.get_log_timeout(timeout)
    close_client = client is None
    client = client or httpx.Client()

    try:
        response = client.post(endpoint_url, json=payload, timeout=timeout_val)
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        raise LogSendError(f"로그 전송 실패: {exc}") from exc
    finally:
        if close_client:
            client.close()
