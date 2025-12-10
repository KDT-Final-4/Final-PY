"""API v1 router with grouped endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import content, coupang, publish, ssadagu, trends

router = APIRouter()

router.include_router(trends.router)
router.include_router(coupang.router)
router.include_router(ssadagu.router)
router.include_router(content.router)
router.include_router(publish.router)

__all__ = ["router"]
