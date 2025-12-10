"""Schemas for trending keywords."""

from typing import Literal

from pydantic import BaseModel, Field


class TrendKeyword(BaseModel):
    """Represents a single trending keyword."""

    keyword: str = Field(..., description="트렌드 키워드")
    score: float | None = Field(None, description="인기도 점수 또는 비율")


class GoogleTrendItem(BaseModel):
    """Google 트렌드 항목."""

    categoryId: int = Field(1, description="카테고리 ID (기본 1)")
    keyword: str = Field(..., description="트렌드 키워드")
    searchVolume: int = Field(0, description="검색량 정보 (미수집 시 0)")
    snsType: Literal["google"] = Field(
        "google", description="트렌드 출처 (현재는 google 고정)"
    )


class GoogleCrawlerResponse(BaseModel):
    """Google 트렌드 응답 포맷."""

    googleCrawler: list[GoogleTrendItem] = Field(
        ..., description="구글 트렌드 크롤러 결과 리스트"
    )
