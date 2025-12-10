from fastapi.testclient import TestClient

from app.api.v1.endpoints.ssadagu import get_ssadagu_service
from app.main import app
from app.schemas.products import SsadaguProduct
from app.services.ssadagu import SsadaguService


class DummySsadaguService(SsadaguService):
    async def search(self, keyword: str, **kwargs):
        return [
            SsadaguProduct(
                title=f"{keyword}-title",
                price=12345.0,
                product_link="https://ssadagu.kr/product/1",
                thumbnail_link="https://ssadagu.kr/images/1.jpg",
                detail_specs={"spec1": "value1"},
            )
        ]


class EmptySsadaguService(SsadaguService):
    async def search(self, keyword: str, **kwargs):
        return []


def test_ssadagu_search_returns_expected_format():
    app.dependency_overrides[get_ssadagu_service] = lambda: DummySsadaguService()
    client = TestClient(app)

    resp = client.get("/api/ssadagu/search", params={"keyword": "phone"})

    assert resp.status_code == 200
    data = resp.json()
    assert "싸다구" in data
    assert isinstance(data["싸다구"], list)
    first = data["싸다구"][0]
    assert first["title"] == "phone-title"
    assert first["price"] == 12345.0
    assert first["product_link"].startswith("https://")
    assert first["thumbnail_link"].startswith("https://")
    assert first["detail_specs"]["spec1"] == "value1"

    app.dependency_overrides.clear()


def test_ssadagu_search_returns_502_on_empty():
    app.dependency_overrides[get_ssadagu_service] = lambda: EmptySsadaguService()
    client = TestClient(app)

    resp = client.get("/api/ssadagu/search", params={"keyword": "phone"})

    assert resp.status_code == 502
    app.dependency_overrides.clear()
