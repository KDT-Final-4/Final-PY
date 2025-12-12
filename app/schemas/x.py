"""X(Twitter) 게시용 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class XPublishRequest(BaseModel):
    """게시에 필요한 제목/본문을 받고, 필요 시 OAuth 키 4개를 오버라이드 입력."""

    title: str = Field(..., description="글 제목")
    content: str = Field(..., description="글 본문 (280자 내외로 조정됨)")
    consumer_key: str | None = Field(None, description="X API consumer key (없으면 환경변수)")
    consumer_secret: str | None = Field(None, description="X API consumer secret (없으면 환경변수)")
    access_token: str | None = Field(None, description="X API access token (없으면 환경변수)")
    access_token_secret: str | None = Field(None, description="X API access token secret (없으면 환경변수)")


class XPublishResponse(BaseModel):
    success: bool
    message: str
    url: HttpUrl | None = None
