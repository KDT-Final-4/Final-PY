"""Service for Ssadagu crawling."""

from collections.abc import Sequence

from app.schemas.products import ProductDetail, ProductSummary


class SsadaguService:
    """Stub service for Ssadagu scraping."""

    async def search(self, keyword: str) -> Sequence[ProductSummary]:
        """Search Ssadagu products by keyword."""
        raise NotImplementedError("싸다구 검색이 아직 구현되지 않았습니다.")

    async def fetch_details(self, url: str) -> ProductDetail:
        """Fetch product details from a Ssadagu product page."""
        raise NotImplementedError("싸다구 상세 크롤링이 아직 구현되지 않았습니다.")
