"""업로드 채널 설정 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadChannelSettings(BaseModel):
    """업로드 채널 세팅."""

    id: int
    userId: int
    name: str = Field(..., description="채널 이름")
    channel: str = Field(..., description="플랫폼 식별자 (예: naver_blog, x)")
    apiKey: str | None = Field(None, description="채널별 필요 시 사용하는 API Key 또는 토큰")
    status: str = Field(..., description="상태 (예: active/inactive)")
    createdAt: str
    updatedAt: str

    # 채널별 옵션 (필요한 것만 사용)
    naver_login_id: str | None = Field(None, description="네이버 블로그 로그인 ID")
    naver_login_pw: str | None = Field(None, description="네이버 블로그 로그인 PW")
    naver_blog_id: str | None = Field(None, description="블로그 ID (미지정 시 login_id 사용)")

    x_consumer_key: str | None = Field(None, description="X consumer key")
    x_consumer_secret: str | None = Field(None, description="X consumer secret")
    x_access_token: str | None = Field(None, description="X access token")
    x_access_token_secret: str | None = Field(None, description="X access token secret")
