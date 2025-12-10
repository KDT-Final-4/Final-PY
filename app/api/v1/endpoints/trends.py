"""Trending keyword endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.trends import TrendKeyword
from app.services.trends import GoogleTrendsService

router = APIRouter(prefix="/trends", tags=["trends"])


def get_trends_service() -> GoogleTrendsService:
    """Provide a trends service instance."""
    return GoogleTrendsService()


@router.get(
    "/",
    response_model=list[TrendKeyword],
    summary="구글 트렌드 키워드 가져오기",
    description="구글 트렌드를 크롤링하여 상위 키워드를 제공합니다.",
)
async def list_trending_keywords(
    service: GoogleTrendsService = Depends(get_trends_service),
) -> list[TrendKeyword]:
    """Return trending keywords. Implementation is intentionally deferred."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="트렌드 수집 기능은 아직 구현되지 않았습니다.",
    )
