"""X(Twitter) 게시 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.x import XPublishRequest, XPublishResponse
from app.services.x_post import XPostService

router = APIRouter(prefix="/x", tags=["x"])


def get_x_post_service() -> XPostService:
    return XPostService()


@router.post("/publish", response_model=XPublishResponse, summary="X(트위터) 글 게시")
async def publish_x(
    body: XPublishRequest,
    service: XPostService = Depends(get_x_post_service),
) -> XPublishResponse:
    try:
        url = await service.post_async(
            title=body.title,
            content=body.content,
            consumer_key=body.consumer_key,
            consumer_secret=body.consumer_secret,
            access_token=body.access_token,
            access_token_secret=body.access_token_secret,
        )
        return XPublishResponse(success=True, message="업로드 성공", url=url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"X 업로드 실패: {exc}",
        )
