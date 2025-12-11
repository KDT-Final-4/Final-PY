"""프로모션 생성용 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.llm import LlmSetting
from app.schemas.products import SsadaguProduct


class PromoRequest(BaseModel):
    """프로모션 생성 요청."""

    product: SsadaguProduct = Field(..., description="선택된 싸다구 상품 정보")
    platform: str = Field("naver_blog", description="생성 대상 플랫폼 (naver_blog, x 등)")
    llm_setting: LlmSetting | None = Field(
        None, description="LLM 설정 (모델/온도/API Key/추가 프롬프트 등)"
    )


class PromoResponse(BaseModel):
    """생성된 홍보글."""

    title: str
    body: str
    link: str = Field(..., description="사용된 상품 링크")
    platform: str = Field(..., description="생성된 플랫폼")
