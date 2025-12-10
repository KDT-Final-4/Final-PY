"""Coupang scraping endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.products import ProductDetail, ProductSummary
from app.services.coupang import CoupangService

router = APIRouter(prefix="/coupang", tags=["coupang"])


def get_coupang_service() -> CoupangService:
    """Provide a Coupang service instance."""
    return CoupangService()


@router.get(
    "/search",
    response_model=list[ProductSummary],
    summary="쿠팡 검색 결과 목록 가져오기",
)
async def search_coupang(
    keyword: str = Query(..., description="검색할 키워드"),
    service: CoupangService = Depends(get_coupang_service),
) -> list[ProductSummary]:
    """Search Coupang by keyword. Implementation is intentionally deferred."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="쿠팡 검색 기능은 아직 구현되지 않았습니다.",
    )


@router.get(
    "/detail",
    response_model=ProductDetail,
    summary="쿠팡 상품 상세 가져오기",
)
async def get_coupang_detail(
    url: str = Query(..., description="상품 상세 URL"),
    service: CoupangService = Depends(get_coupang_service),
) -> ProductDetail:
    """Fetch Coupang product detail including OCR content."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="쿠팡 상세 크롤링 기능은 아직 구현되지 않았습니다.",
    )
