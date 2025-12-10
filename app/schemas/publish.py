"""Schemas for publishing content to external platforms."""

from pydantic import BaseModel, Field, HttpUrl


class PublishRequest(BaseModel):
    """Payload for publishing generated content."""

    platform: str = Field(..., description="업로드할 플랫폼 (naver_blog, x 등)")
    title: str = Field(..., description="게시글 제목")
    content: str = Field(..., description="게시할 본문")


class PublishResult(BaseModel):
    """Result of a publish attempt."""

    platform: str = Field(..., description="업로드된 플랫폼")
    status: str = Field(..., description="처리 상태 (예: pending, success, failed)")
    url: HttpUrl | None = Field(None, description="게시글 URL (성공 시)")
