"""Ssadagu scraping endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.products import ProductDetail, ProductSummary
from app.services.ssadagu import SsadaguService

router = APIRouter(prefix="/ssadagu", tags=["ssadagu"])


def get_ssadagu_service() -> SsadaguService:
    """Provide a Ssadagu service instance."""
    return SsadaguService()


@router.get(
    "/search",
    response_model=list[ProductSummary],
    summary="싸다구 검색 결과 목록 가져오기",
)
async def search_ssadagu(
    keyword: str = Query(..., description="검색할 키워드"),
    service: SsadaguService = Depends(get_ssadagu_service),
) -> list[ProductSummary]:
    """Search ssadagu by keyword."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="싸다구 검색 기능은 아직 구현되지 않았습니다.",
    )


@router.get(
    "/detail",
    response_model=ProductDetail,
    summary="싸다구 상품 상세 가져오기",
)
async def get_ssadagu_detail(
    url: str = Query(..., description="상품 상세 URL"),
    service: SsadaguService = Depends(get_ssadagu_service),
) -> ProductDetail:
    """Fetch ssadagu product detail."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="싸다구 상세 크롤링 기능은 아직 구현되지 않았습니다.",
    )
