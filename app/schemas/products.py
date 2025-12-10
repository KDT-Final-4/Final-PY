"""Schemas for product data."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class SsadaguProduct(BaseModel):
    """싸다구 검색 결과 아이템."""

    title: str = Field(..., description="제품 제목")
    price: float | None = Field(None, description="가격 정보 (숫자)")
    product_link: HttpUrl = Field(..., description="제품 상세 링크")
    thumbnail_link: HttpUrl | None = Field(None, description="썸네일 링크")
    detail_specs: dict[str, str] = Field(
        default_factory=dict, description="상세 스펙 (키-값 자유 형식)"
    )


class SsadaguSearchResponse(BaseModel):
    """싸다구 검색 응답 포맷."""

    products: list[SsadaguProduct] = Field(..., alias="싸다구", description="싸다구 검색 결과")

    model_config = ConfigDict(populate_by_name=True)
