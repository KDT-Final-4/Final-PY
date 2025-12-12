"""Lightweight log sender that posts to an external service and prints locally.

Environment variables (loaded from .env via app.config):
    LOG_ENDPOINT (필수): 로그를 전송할 HTTP 엔드포인트(URL).
    LOG_SOURCE (선택): 로그 발생 소스 식별자. 기본값 "final-py".
    LOG_TIMEOUT (선택): 요청 타임아웃(초). 기본 5.0.

로그 전송 형식(요청 JSON):
{
  "userId": 0,
  "logType": "INFO" | "WARN" | "ERROR",
  "loggedProcess": "string",
  "loggedDate": "2025-12-12T05:10:56.490Z",
  "message": "string",
  "submessage": "string",
  "jobId": "string"
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
from app import config

class LogSendError(RuntimeError):
    """Raised when a log cannot be delivered to the remote endpoint."""


def send_log(
    *,
    message: str,
    level: str = "INFO",
    submessage: str = "",
    logged_process: str = "",
    user_id: int = 0,
    job_id: str = "",
    endpoint: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.Client] = None,
) -> httpx.Response:
    """외부 로그 수집기로 전송하고 콘솔에도 출력한다.

    Args:
        message: 전송할 메시지.
        level: 로그 레벨 문자열. INFO/WARN/ERROR 중 하나.
        submessage: 부가 메시지.
        logged_process: 어떤 프로세스/기능에서 발생한 로그인지 식별자.
        user_id: 사용자 ID (없으면 0).
        job_id: 배치/작업 ID 등 향후 확장용 문자열.
        endpoint: 명시적 엔드포인트. 없으면 LOG_ENDPOINT 사용.
        timeout: 요청 타임아웃(초). 없으면 LOG_TIMEOUT 또는 5.0초.
        client: 재사용할 httpx.Client. 없으면 내부에서 생성 후 닫는다.
    """

    log_level = level.upper()
    if log_level not in {"INFO", "WARN", "ERROR"}:
        log_level = "INFO"

    payload = {
        "userId": user_id,
        "logType": log_level,
        "loggedProcess": logged_process or config.get_log_source(),
        "loggedDate": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "submessage": submessage,
        "jobId": job_id,
    }

    # 즉시 로컬 콘솔 확인
    print(f"[LOG][{payload['logType']}] {payload['loggedProcess']} | {payload['message']} | {payload['submessage']}")

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
