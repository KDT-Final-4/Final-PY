"""Pydantic schemas."""

from app.schemas.content import ContentDraft, ContentRequest
from app.schemas.products import ProductDetail, ProductSummary
from app.schemas.publish import PublishRequest, PublishResult
from app.schemas.trends import (
    GoogleCrawlerResponse,
    GoogleTrendItem,
    TrendKeyword,
)

__all__ = [
    "ContentDraft",
    "ContentRequest",
    "GoogleCrawlerResponse",
    "GoogleTrendItem",
    "ProductDetail",
    "ProductSummary",
    "PublishRequest",
    "PublishResult",
    "TrendKeyword",
]
