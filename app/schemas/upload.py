"""업로드 채널 설정 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime


class UploadChannelSettings(BaseModel):
    """업로드 채널 세팅."""

    id: int
    userId: int
    name: str = Field(..., description="플랫폼 식별자 (예: NAVER, X)")
    apiKey: str | None = Field(
        None, description="채널별 필요 시 사용하는 API Key 또는 토큰"
    )
    status: bool = Field(True, description="상태 (예: active/inactive)")
    createdAt: datetime
    updatedAt: datetime

    # 채널별 옵션 (필요한 것만 사용)
    client_id: str | None = Field(None, description="네이버 블로그 로그인 ID")
    client_pw: str | None = Field(None, description="네이버 블로그 로그인 PW")
    naver_blog_id: str | None = Field(
        None, description="블로그 ID (미지정 시 login_id 사용)"
    )

    x_consumer_key: str | None = Field(None, description="X consumer key")
    x_consumer_secret: str | None = Field(None, description="X consumer secret")
    x_access_token: str | None = Field(None, description="X access token")
    x_access_token_secret: str | None = Field(None, description="X access token secret")


class UploadRequest(BaseModel):
    """업로드 요청."""

    userId: int = Field(1, description="사용자 ID (기본 1)")
    jobId: str = Field(..., description="작업 ID")
    title: str = Field(..., description="제목")
    body: str = Field(..., description="본문")
    keyword: str = Field(..., description="키워드")
    channelName: str = Field(..., description="업로드 채널 이름 (예: NAVER, X)")

    # 선택: 채널별 자격/옵션(없으면 환경 변수 등으로 폴백)
    client_id: str | None = Field(None, description="네이버 로그인 ID")
    client_pw: str | None = Field(None, description="네이버 로그인 PW")
    naver_blog_id: str | None = Field(None, description="네이버 블로그 ID")

    x_consumer_key: str | None = Field(None, description="X consumer key")
    x_consumer_secret: str | None = Field(None, description="X consumer secret")
    x_access_token: str | None = Field(None, description="X access token")
    x_access_token_secret: str | None = Field(None, description="X access token secret")


class UploadResponse(BaseModel):
    """업로드 결과."""

    jobId: str
    link: str
    channel: str
    success: bool = True
    message: str = "업로드 완료"
