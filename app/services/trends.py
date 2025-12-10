"""Service for fetching trending keywords."""

from collections.abc import Sequence

from app.schemas.trends import TrendKeyword


class GoogleTrendsService:
    """Stub service for Google Trends crawling."""

    async def fetch_keywords(self, limit: int = 20) -> Sequence[TrendKeyword]:
        """Retrieve trending keywords from Google Trends."""
        raise NotImplementedError("구글 트렌드 크롤링이 아직 구현되지 않았습니다.")
