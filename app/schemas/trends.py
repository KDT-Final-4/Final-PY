"""Schemas for trending keywords."""

from pydantic import BaseModel, Field


class TrendKeyword(BaseModel):
    """Represents a single trending keyword."""

    keyword: str = Field(..., description="트렌드 키워드")
    score: float | None = Field(None, description="인기도 점수 또는 비율")
