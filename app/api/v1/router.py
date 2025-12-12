"""API v1 router with grouped endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    content,
    keywords,
    llm,
    promo,
    publish,
    relevance,
    ssadagu,
    trends,
    crawler,
    naver_blog,
    x_post,
    upload,
    write,
)

router = APIRouter()

router.include_router(trends.router)
router.include_router(ssadagu.router)
router.include_router(llm.router)
router.include_router(promo.router)
router.include_router(relevance.router)
router.include_router(keywords.router)
router.include_router(content.router)
router.include_router(publish.router)
router.include_router(naver_blog.router)
router.include_router(x_post.router)
router.include_router(crawler.router)
router.include_router(upload.router)
router.include_router(write.router)

__all__ = ["router"]
