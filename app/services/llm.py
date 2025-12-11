"""LLM 서비스 (langchain_openai.ChatOpenAI 기반)."""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_openai_api_key


class LLMService:
    """시스템 프롬프트와 사용자 입력을 받아 답변을 생성한다."""

    def __init__(self, model: str | None = None, temperature: float | None = None, api_key: str | None = None):
        self.model = model or "gpt-4o-mini"
        self.temperature = temperature if temperature is not None else 0.5
        self.api_key = api_key or get_openai_api_key()
        self.client = ChatOpenAI(model=self.model, temperature=self.temperature, api_key=self.api_key)

    async def chat(
        self,
        system_prompt: str,
        user_input: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
    ) -> str:
        """LLM 호출."""
        client = self.client
        if model or temperature is not None or api_key is not None:
            client = ChatOpenAI(
                model=model or self.model,
                temperature=self.temperature if temperature is None else temperature,
                api_key=api_key or self.api_key,
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
        response = await client.ainvoke(messages)
        return response.content
