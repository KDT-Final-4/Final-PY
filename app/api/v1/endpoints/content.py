"""Content generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.content import ContentDraft, ContentRequest
from app.services.content import ContentService

router = APIRouter(prefix="/content", tags=["content"])


def get_content_service() -> ContentService:
    """Provide a content service instance."""
    return ContentService()


@router.post(
    "/draft",
    response_model=ContentDraft,
    summary="홍보글 초안 생성하기",
)
async def generate_content(
    payload: ContentRequest,
    service: ContentService = Depends(get_content_service),
) -> ContentDraft:
    """Generate promotional content for a platform."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="콘텐츠 생성 기능은 아직 구현되지 않았습니다.",
    )
