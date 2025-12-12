from fastapi.testclient import TestClient

from app.api.v1.endpoints.keywords import get_keyword_service
from app.main import app
from app.services.keywords import KeywordService
from app.services.llm import LLMService


class DummyLLMService(LLMService):
    async def chat(self, system_prompt: str, user_input: str, **kwargs) -> str:  # type: ignore[override]
        return '{"keyword": "트렌드", "real_keyword": "트렌드 추천 상품", "reason": "쇼핑 검색어로 자연스러움"}'


class DummyKeywordService(KeywordService):
    def __init__(self):
        super().__init__(llm_service=DummyLLMService(api_key="test"))


def test_keyword_refine_returns_real_keyword():
    app.dependency_overrides[get_keyword_service] = lambda: DummyKeywordService()
    client = TestClient(app)

    resp = client.post(
        "/api/keywords/refine",
        json={
            "google_trends": [
                {"categoryId": 1, "keyword": "트렌드", "searchVolume": 0, "snsType": "google"},
                {"categoryId": 1, "keyword": "연필", "searchVolume": 0, "snsType": "google"},
            ],
            "llm_setting": None,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["keyword"] == "트렌드"
    assert data["real_keyword"] == "트렌드 추천 상품"
    assert "reason" in data

    app.dependency_overrides.clear()
