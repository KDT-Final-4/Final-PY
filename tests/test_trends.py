from fastapi.testclient import TestClient

from app.api.v1.endpoints.trends import get_trends_service
from app.main import app
from app.schemas.trends import GoogleCrawlerResponse, GoogleTrendItem
from app.services.trends import GoogleTrendsService


class DummyTrendsService(GoogleTrendsService):
    async def fetch_google_crawler_response(self, *, limit: int = 20, **kwargs):
        return [
            GoogleTrendItem(
                categoryId=1,
                keyword=f"kw-{idx}",
                searchVolume=0,
                snsType="google",
            )
            for idx in range(limit)
        ]


def test_trends_endpoint_returns_google_crawler_format():
    app.dependency_overrides[get_trends_service] = lambda: DummyTrendsService()
    client = TestClient(app)

    response = client.get("/api/trends?limit=2")

    assert response.status_code == 200
    data = GoogleCrawlerResponse.model_validate(response.json())
    assert len(data.googleCrawler) == 2
    assert data.googleCrawler[0].categoryId == 1
    assert data.googleCrawler[0].snsType == "google"
    assert data.googleCrawler[0].keyword == "kw-0"

    app.dependency_overrides.clear()
