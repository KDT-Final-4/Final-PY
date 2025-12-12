"""키워드-상품 연관도 평가 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.llm import LlmSetting
from app.schemas.products import SsadaguProduct


class RelevanceRequest(BaseModel):
    keyword: str = Field(..., description="검색 키워드")
    product: SsadaguProduct = Field(..., description="싸다구 상품 정보")
    llm_setting: LlmSetting | None = Field(None, description="LLM 설정(선택)")


class RelevanceResponse(BaseModel):
    keyword: str
    product_title: str
    score: float = Field(..., description="연관도 점수(0.0~1.0)")
    reason: str = Field(..., description="판단 근거")
