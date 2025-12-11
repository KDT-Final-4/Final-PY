"""Naver Blog publish endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.content import (
    NaverBlogPublishRequest,
    NaverBlogPublishResponse,
)
from app.services.naver_blog import NaverBlogPublishResult, NaverBlogService

router = APIRouter(prefix="/naver-blog", tags=["naver-blog"])


def get_naver_blog_service() -> NaverBlogService:
    return NaverBlogService()


@router.post(
    "/publish",
    response_model=NaverBlogPublishResponse,
    summary="네이버 블로그에 글 업로드",
)
async def publish_naver_blog(
    payload: NaverBlogPublishRequest,
    service: NaverBlogService = Depends(get_naver_blog_service),
) -> NaverBlogPublishResponse:
    """
    네이버 로그인 → 블로그 글 작성 → 발행까지 수행한다.
    blog_id가 없으면 login_id를 사용한다.
    """
    result: NaverBlogPublishResult = await service.publish(
        login_id=payload.login_id,
        login_pw=payload.login_pw,
        title=payload.title,
        content=payload.content,
        blog_id=payload.blog_id,
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.message,
        )
    return NaverBlogPublishResponse(
        success=True,
        message=result.message,
        url=result.url,
    )
