"""중앙 환경 변수 관리 모듈.

.env가 존재하면 자동으로 로드하며, 각 설정은 전용 getter를 통해 조회한다.
새 환경 변수가 필요하면 이 파일에 추가한다.
"""

from __future__ import annotations

import os
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# .env 파일을 우선 로드하여 os.environ에 반영
load_dotenv()

# 환경 변수 키
LOG_ENDPOINT_KEY = "LOG_ENDPOINT"
LOG_SOURCE_KEY = "LOG_SOURCE"
LOG_TIMEOUT_KEY = "LOG_TIMEOUT"
LOG_TREND_ENDPOINT_KEY = "LOG_TREND_ENDPOINT"
OPENAI_API_KEY_KEY = "OPENAI_API_KEY"
X_CONSUMER_KEY = "X_CONSUMER_KEY"
X_CONSUMER_SECRET = "X_CONSUMER_SECRET"
X_ACCESS_TOKEN = "X_ACCESS_TOKEN"
X_ACCESS_TOKEN_SECRET = "X_ACCESS_TOKEN_SECRET"


def _get_required_str(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise ValueError(f"{name} 환경 변수가 필요합니다.")
    return value


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 환경 변수는 숫자여야 합니다.") from exc


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 환경 변수는 정수여야 합니다.") from exc


def _get_list_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---- 로그 관련 설정 ----
def get_log_endpoint(override: Optional[str] = None) -> str:
    """로그 전송 엔드포인트. override가 없으면 LOG_ENDPOINT를 사용."""
    endpoint = override or _get_required_str(LOG_ENDPOINT_KEY)
    return endpoint.rstrip("/")


def get_log_source(override: Optional[str] = None) -> str:
    """로그 소스 식별자. override가 없으면 LOG_SOURCE 또는 기본값 사용."""
    return override or os.getenv(LOG_SOURCE_KEY, "final-py")


def get_log_timeout(override: Optional[float] = None) -> float:
    """로그 전송 타임아웃(초). override가 없으면 LOG_TIMEOUT 또는 기본값 사용."""
    if override is not None:
        return override
    return _get_float_env(LOG_TIMEOUT_KEY, 5.0)


def get_log_trend_endpoint(override: Optional[str] = None) -> str:
    """
    트렌드 콜백 전송 엔드포인트.
    우선순위: override > LOG_TREND_ENDPOINT > LOG_ENDPOINT 기반 파생(/trend)
    """
    if override:
        return override.rstrip("/")

    env_value = os.getenv(LOG_TREND_ENDPOINT_KEY)
    if env_value:
        return env_value.rstrip("/")

    base = get_log_endpoint()
    parsed = urlparse(base)
    path = parsed.path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    if parts and parts[-1] == "log":
        parts[-1] = "trend"
    else:
        parts.append("trend")
    new_path = "/" + "/".join(parts)
    return urlunparse(parsed._replace(path=new_path))


# ---- OpenAI 설정 ----
def get_openai_api_key(override: Optional[str] = None) -> str:
    """OpenAI API Key 조회 (필수)."""
    return override or _get_required_str(OPENAI_API_KEY_KEY)


# ---- X(OAuth1) 설정 ----
def get_x_consumer_key(override: Optional[str] = None) -> str:
    return override or _get_required_str(X_CONSUMER_KEY)


def get_x_consumer_secret(override: Optional[str] = None) -> str:
    return override or _get_required_str(X_CONSUMER_SECRET)


def get_x_access_token(override: Optional[str] = None) -> str:
    return override or _get_required_str(X_ACCESS_TOKEN)


def get_x_access_token_secret(override: Optional[str] = None) -> str:
    return override or _get_required_str(X_ACCESS_TOKEN_SECRET)


__all__ = [
    "LOG_ENDPOINT_KEY",
    "LOG_SOURCE_KEY",
    "LOG_TIMEOUT_KEY",
    "LOG_TREND_ENDPOINT_KEY",
    "OPENAI_API_KEY_KEY",
    "X_CONSUMER_KEY",
    "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "get_log_endpoint",
    "get_log_source",
    "get_log_timeout",
    "get_log_trend_endpoint",
    "get_openai_api_key",
    "get_x_consumer_key",
    "get_x_consumer_secret",
    "get_x_access_token",
    "get_x_access_token_secret",
]
