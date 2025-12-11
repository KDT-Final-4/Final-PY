from fastapi.testclient import TestClient

from app.api.v1.endpoints.naver_blog import get_naver_blog_service
from app.main import app
from app.schemas.content import NaverBlogPublishRequest
from app.services.naver_blog import NaverBlogPublishResult, NaverBlogService


class DummyNaverBlogService(NaverBlogService):
    async def publish(self, **kwargs):
        return NaverBlogPublishResult(True, "ok", url="https://blog.naver.com/post/1")


class FailingNaverBlogService(NaverBlogService):
    async def publish(self, **kwargs):
        return NaverBlogPublishResult(False, "fail")


def test_naver_blog_publish_success():
    app.dependency_overrides[get_naver_blog_service] = lambda: DummyNaverBlogService()
    client = TestClient(app)

    payload = {
        "login_id": "user",
        "login_pw": "pw",
        "title": "hello",
        "content": "world",
    }
    resp = client.post("/api/naver-blog/publish", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["url"].startswith("https://")

    app.dependency_overrides.clear()


def test_naver_blog_publish_failure_returns_502():
    app.dependency_overrides[get_naver_blog_service] = lambda: FailingNaverBlogService()
    client = TestClient(app)

    payload = {
        "login_id": "user",
        "login_pw": "pw",
        "title": "hello",
        "content": "world",
    }
    resp = client.post("/api/naver-blog/publish", json=payload)

    assert resp.status_code == 502

    app.dependency_overrides.clear()
