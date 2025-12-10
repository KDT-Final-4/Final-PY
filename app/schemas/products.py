"""Schemas for product data."""

from pydantic import BaseModel, Field, HttpUrl


class ProductSummary(BaseModel):
    """Minimal product information from a search result."""

    title: str = Field(..., description="상품명")
    url: HttpUrl = Field(..., description="상품 상세 페이지 URL")
    price: float | None = Field(None, description="가격 정보")
    source: str = Field(..., description="데이터 출처 (쿠팡/싸다구 등)")


class ProductDetail(ProductSummary):
    """Detailed product information including scraped description."""

    description: str | None = Field(None, description="상품 설명 또는 OCR 추출 텍스트")
    images: list[HttpUrl] | None = Field(None, description="상품 이미지 URL 목록")
