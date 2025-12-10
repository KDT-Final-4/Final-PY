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


def test_extract_keywords_from_response_models_and_dicts():
    service = GoogleTrendsService()
    model_response = GoogleCrawlerResponse(
        googleCrawler=[
            GoogleTrendItem(categoryId=1, keyword="alpha", searchVolume=0, snsType="google"),
            GoogleTrendItem(categoryId=1, keyword="beta", searchVolume=0, snsType="google"),
            GoogleTrendItem(categoryId=1, keyword="alpha", searchVolume=0, snsType="google"),
        ]
    )
    dict_response = {
        "googleCrawler": [
            {"categoryId": 1, "keyword": "gamma", "searchVolume": 0, "snsType": "google"}
        ]
    }

    assert service.extract_keywords_from_response(model_response) == ["alpha", "beta"]
    assert service.extract_keywords_from_response(dict_response) == ["gamma"]


def test_extract_keywords_handles_invalid_payload():
    service = GoogleTrendsService()
    invalid_payload = {"googleCrawler": [{"keyword": 123}]}

    assert service.extract_keywords_from_response(None) == []
    assert service.extract_keywords_from_response(invalid_payload) == []


def test_extract_endpoint_returns_keyword_list():
    app.dependency_overrides[get_trends_service] = lambda: GoogleTrendsService()
    client = TestClient(app)
    payload = {
        "googleCrawler": [
            {"categoryId": 1, "keyword": "one", "searchVolume": 0, "snsType": "google"},
            {"categoryId": 1, "keyword": "two", "searchVolume": 0, "snsType": "google"},
            {"categoryId": 1, "keyword": "one", "searchVolume": 0, "snsType": "google"},
        ]
    }

    resp = client.post("/api/trends/extract", json=payload)

    assert resp.status_code == 200
    assert resp.json() == ["one", "two"]
    app.dependency_overrides.clear()
