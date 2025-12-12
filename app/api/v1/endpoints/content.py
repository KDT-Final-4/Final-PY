"""Content generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.logs import async_send_log
from app.schemas.content import ContentDraft, ContentRequest, ContentLinkUpdate
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


@router.patch(
    "/link",
    response_model=ContentLinkUpdate,
    summary="업로드된 콘텐츠 링크 콜백 수신",
)
async def update_content_link(payload: ContentLinkUpdate) -> ContentLinkUpdate:
    """업로드 후 링크를 받아 저장/로그용으로 사용."""
    await async_send_log(
        message="콘텐츠 링크 수신",
        logged_process="content",
        job_id=payload.jobId,
        submessage=payload.link,
    )
    return payload
