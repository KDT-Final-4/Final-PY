from fastapi.testclient import TestClient

from app.api.v1.endpoints.llm import get_llm_service
from app.main import app
from app.services.llm import LLMService


class DummyLLMService(LLMService):
    async def chat(self, system_prompt: str, user_input: str, **kwargs) -> str:  # type: ignore[override]
        return f"[dummy]{system_prompt}|{user_input}"


def test_llm_chat_returns_answer():
    app.dependency_overrides[get_llm_service] = lambda: DummyLLMService(api_key="test")
    client = TestClient(app)

    resp = client.post(
        "/api/llm/chat",
        json={"system_prompt": "sys", "user_input": "hi"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "[dummy]sys|hi"
    app.dependency_overrides.clear()


def test_llm_chat_uses_setting_fallbacks():
    app.dependency_overrides[get_llm_service] = lambda: DummyLLMService(api_key="test")
    client = TestClient(app)

    resp = client.post(
        "/api/llm/chat",
        json={
            "system_prompt": "",
            "user_input": "hello",
            "llm_setting": {
                "id": 1,
                "userId": 10,
                "name": "default",
                "modelName": "gpt-4o-mini",
                "status": True,
                "maxTokens": "1024",
                "temperature": 0.7,
                "prompt": "sys-from-setting",
                "apiKey": "k",
                "generationType": "chat",
                "createdAt": "now",
                "updatedAt": "now",
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "[dummy]sys-from-setting|hello"
    app.dependency_overrides.clear()
