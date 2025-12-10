"""Trending keyword endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.trends import GoogleCrawlerResponse
from app.services.trends import GoogleTrendsService

router = APIRouter(prefix="/trends", tags=["trends"])


def get_trends_service() -> GoogleTrendsService:
    """Provide a trends service instance."""
    return GoogleTrendsService()


@router.get(
    "/",
    response_model=GoogleCrawlerResponse,
    summary="구글 트렌드 키워드 가져오기",
    description="구글 트렌드를 크롤링하여 상위 키워드를 제공합니다.",
)
async def list_trending_keywords(
    limit: int = Query(20, ge=1, le=100, description="가져올 최대 키워드 수"),
    service: GoogleTrendsService = Depends(get_trends_service),
) -> GoogleCrawlerResponse:
    """Return trending keywords in googleCrawler 포맷으로 제공합니다."""
    items = await service.fetch_google_crawler_response(limit=limit)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="구글 트렌드 키워드를 가져오지 못했습니다.",
        )
    return GoogleCrawlerResponse(googleCrawler=items)
