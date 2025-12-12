"""글 작성 오케스트레이션 요청/응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.llm import LlmSetting
from app.schemas.upload import UploadChannelSettings


class WriteRequest(BaseModel):
    """글 작성 요청."""

    userId: int = Field(1, description="사용자 ID (기본 1)")
    llmSettings: LlmSetting
    uploadChannels: UploadChannelSettings
    keyword: str | None = Field(None, description="검색 키워드 (없으면 트렌드에서 생성)")
    jobId: str = Field(..., description="작업 ID")


class WriteResponse(BaseModel):
    """글 작성 결과."""

    jobId: str
    keyword: str
    product_title: str
    link: str
    status: str = "OK"
