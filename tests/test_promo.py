from fastapi.testclient import TestClient

from app.api.v1.endpoints.promo import get_promo_service
from app.main import app
from app.schemas.products import SsadaguProduct
from app.services.llm import LLMService
from app.services.promo import PromoService


class DummyLLMService(LLMService):
    async def chat(self, system_prompt: str, user_input: str, **kwargs) -> str:  # type: ignore[override]
        return '{"title": "promo-title", "body": "promo-body"}'


class DummyPromoService(PromoService):
    def __init__(self):
        super().__init__(llm_service=DummyLLMService(api_key="test"))


def test_promo_creates_blog_from_product():
    app.dependency_overrides[get_promo_service] = lambda: DummyPromoService()
    client = TestClient(app)

    product = {
        "title": "테스트 상품",
        "price": 10000.0,
        "product_link": "https://ssadagu.kr/item/1",
        "thumbnail_link": "https://ssadagu.kr/thumb.jpg",
        "detail_specs": {"색상": "블랙"},
    }

    resp = client.post(
        "/api/promo/ssadagu/blog",
        json={
            "product": product,
            "platform": "naver_blog",
            "llm_setting": None,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "promo-title"
    assert data["body"] == "promo-body"
    assert data["link"] == product["product_link"]
    assert data["platform"] == "naver_blog"

    app.dependency_overrides.clear()
