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
    user_id: int = 1,
    job_id: str = "",
    endpoint: Optional[str] = None,
    source: Optional[str] = None,
    meta: Optional[dict] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.Client] = None,
    raise_on_error: bool = False,
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
        source: 호환성용. 없으면 LOG_SOURCE.
        meta: 호환성용 임의 데이터(dict). 페이로드에 meta/level/source/timestamp도 함께 포함.
        timeout: 요청 타임아웃(초). 없으면 LOG_TIMEOUT 또는 5.0초.
        client: 재사용할 httpx.Client. 없으면 내부에서 생성 후 닫는다.
        raise_on_error: True면 전송 실패 시 예외를 올린다. 기본 False면 콘솔에만 남김.
    """

    log_level = level.upper()
    if log_level not in {"INFO", "WARN", "ERROR"}:
        log_level = "INFO"

    meta = meta or {}
    now_str = _now_str()
    payload = {
        "userId": user_id,
        "logType": log_level,
        "loggedProcess": logged_process or source or config.get_log_source(),
        "loggedDate": now_str,
        "message": message,
        "submessage": submessage,
        "jobId": job_id,
        # 호환성 필드 (기존 테스트/사용처 대응)
        "level": log_level,
        "meta": meta,
        "source": source or config.get_log_source(),
        "timestamp": now_str,
    }

    # 즉시 로컬 콘솔 확인
    print(
        f"[LOG][{payload['logType']}] {payload['message']} | {payload['loggedProcess']} | {payload['submessage']} | meta={payload['meta']}"
    )

    try:
        endpoint_url = config.get_log_endpoint(endpoint)
    except Exception:
        # 로그 엔드포인트 미설정 시 콘솔만 출력하고 반환
        if not raise_on_error:
            return None  # type: ignore[return-value]
        raise

    timeout_val = config.get_log_timeout(timeout)
    close_client = client is None
    client = client or httpx.Client()

    try:
        response = client.post(endpoint_url, json=payload, timeout=timeout_val)
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        print(f"[LOG][{log_level}] 전송 실패: {exc}")
        if raise_on_error:
            raise LogSendError(f"로그 전송 실패: {exc}") from exc
        return None  # type: ignore[return-value]
    finally:
        if close_client:
            client.close()


async def async_send_log(
    *,
    message: str,
    level: str = "INFO",
    submessage: str = "",
    logged_process: str = "",
    user_id: int = 1,
    job_id: str = "",
    endpoint: Optional[str] = None,
    source: Optional[str] = None,
    meta: Optional[dict] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.AsyncClient] = None,
    raise_on_error: bool = False,
) -> Optional[httpx.Response]:
    """비동기 버전의 send_log."""
    log_level = level.upper()
    if log_level not in {"INFO", "WARN", "ERROR"}:
        log_level = "INFO"

    meta = meta or {}
    now_str = _now_str()
    payload = {
        "userId": user_id,
        "logType": log_level,
        "loggedProcess": logged_process or source or config.get_log_source(),
        "loggedDate": now_str,
        "message": message,
        "submessage": submessage,
        "jobId": job_id,
        "level": log_level,
        "meta": meta,
        "source": source or config.get_log_source(),
        "timestamp": now_str,
    }

    print(
        f"[LOG][{payload['logType']}] {payload['message']} | {payload['loggedProcess']} | {payload['submessage']} | meta={payload['meta']}"
    )

    try:
        endpoint_url = config.get_log_endpoint(endpoint)
    except Exception:
        if not raise_on_error:
            return None
        raise

    timeout_val = config.get_log_timeout(timeout)
    close_client = client is None
    client = client or httpx.AsyncClient()

    try:
        response = await client.post(endpoint_url, json=payload, timeout=timeout_val)
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        print(f"[LOG][{log_level}] 전송 실패: {exc}")
        if raise_on_error:
            raise LogSendError(f"로그 전송 실패: {exc}") from exc
        return None
    finally:
        if close_client:
            await client.aclose()


def _now_str() -> str:
    """Java LocalDateTime 호환(UTC, 밀리초) 포맷 문자열 생성."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
