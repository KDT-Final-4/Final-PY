"""Service for Coupang crawling and OCR extraction."""

from collections.abc import Sequence

from app.schemas.products import ProductDetail, ProductSummary


class CoupangService:
    """Stub service for Coupang scraping and PaddleOCR usage."""

    async def search(self, keyword: str) -> Sequence[ProductSummary]:
        """Search Coupang products by keyword."""
        raise NotImplementedError("쿠팡 검색이 아직 구현되지 않았습니다.")

    async def fetch_details(self, url: str) -> ProductDetail:
        """Fetch product details and OCR text from a Coupang product page."""
        raise NotImplementedError("쿠팡 상세 크롤링이 아직 구현되지 않았습니다.")
