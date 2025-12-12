"""쇼핑몰 검색어 생성 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.llm import LlmSetting


class KeywordRefineRequest(BaseModel):
    trends: list[str] = Field(..., description="구글 트렌드 키워드 리스트")
    llm_setting: LlmSetting | None = Field(None, description="LLM 설정(선택)")


class KeywordRefineResponse(BaseModel):
    keyword: str
    real_keyword: str
    reason: str
