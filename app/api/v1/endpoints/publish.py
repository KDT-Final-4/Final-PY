"""Content publishing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.publish import PublishRequest, PublishResult
from app.services.publish import PublisherService

router = APIRouter(prefix="/publish", tags=["publish"])


def get_publisher_service() -> PublisherService:
    """Provide a publisher service instance."""
    return PublisherService()


@router.post(
    "/",
    response_model=PublishResult,
    summary="플랫폼에 콘텐츠 업로드하기",
)
async def publish_content(
    payload: PublishRequest,
    service: PublisherService = Depends(get_publisher_service),
) -> PublishResult:
    """Publish prepared content to a target platform."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="업로드 기능은 아직 구현되지 않았습니다.",
    )
