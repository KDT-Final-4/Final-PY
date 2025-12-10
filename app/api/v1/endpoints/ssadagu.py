"""Ssadagu scraping endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.products import SsadaguSearchResponse
from app.services.ssadagu import SsadaguService

router = APIRouter(prefix="/ssadagu", tags=["ssadagu"])


def get_ssadagu_service() -> SsadaguService:
    """Provide a Ssadagu service instance."""
    return SsadaguService()


@router.get(
    "/search",
    response_model=SsadaguSearchResponse,
    summary="싸다구 검색 결과 목록 가져오기",
)
async def search_ssadagu(
    keyword: str = Query(..., description="검색할 키워드"),
    service: SsadaguService = Depends(get_ssadagu_service),
) -> SsadaguSearchResponse:
    """Search ssadagu by keyword and return list with detail specs."""
    products = await service.search(keyword)
    if not products:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="싸다구 검색 결과를 가져오지 못했습니다.",
        )
    return SsadaguSearchResponse(products=products)
