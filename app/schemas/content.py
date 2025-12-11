"""Schemas for generated content."""

from pydantic import BaseModel, Field

from app.schemas.products import ProductDetail


class ContentRequest(BaseModel):
    """Input for generating promotional content."""

    title: str = Field(..., description="게시글 제목")
    body: str = Field(..., description="원본 본문 또는 요약")
    ssadagu_product: ProductDetail | None = Field(None, description="싸다구 상품 정보")
    platform: str = Field(..., description="생성 대상 플랫폼 (예: naver_blog, x)")


class ContentDraft(BaseModel):
    """Generated content ready for publishing."""

    platform: str = Field(..., description="대상 플랫폼")
    content: str = Field(..., description="플랫폼 규칙에 맞게 생성된 본문")
