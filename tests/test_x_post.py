from fastapi.testclient import TestClient

from app.api.v1.endpoints.x_post import get_x_post_service
from app.main import app
from app.schemas.x import XPublishRequest
from app.services.x_post import XPostService


class DummyXPostService(XPostService):
    def __init__(self):
        pass

    def post(self, title: str, content: str, **kwargs) -> str:  # type: ignore[override]
        return "https://twitter.com/i/web/status/12345"


def test_x_publish_returns_url():
    app.dependency_overrides[get_x_post_service] = lambda: DummyXPostService()
    client = TestClient(app)

    resp = client.post(
        "/api/x/publish",
        json={"title": "hello", "content": "world"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["url"].startswith("https://twitter.com/i/web/status/")

    app.dependency_overrides.clear()
