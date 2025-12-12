"""쇼핑몰 검색어 생성 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.llm import LlmSetting
from app.schemas.trends import GoogleTrendItem


class KeywordRefineRequest(BaseModel):
    google_trends: list[GoogleTrendItem] = Field(..., description="구글 트렌드 결과 리스트")
    llm_setting: LlmSetting | None = Field(None, description="LLM 설정(선택)")


class KeywordRefineResponse(BaseModel):
    keyword: str
    real_keyword: str
    reason: str
