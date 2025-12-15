"""LLM 요청/응답 스키마."""

from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel, Field


class LLMChatRequest(BaseModel):
    system_prompt: str = Field(..., description="시스템 프롬프트")
    user_input: str = Field(..., description="사용자 입력")
    llm_setting: "LlmSetting | None" = Field(
        None, description="선택적 LLM 설정(모델/온도/API Key 등). 제공 시 우선 적용."
    )


class LLMChatResponse(BaseModel):
    answer: str = Field(..., description="LLM 생성 답변")


class LlmSetting(BaseModel):
    id: int
    userId: int
    name: str
    modelName: str
    status: bool
    maxTokens: int
    temperature: float
    prompt: str | None
    apiKey: str | None
    generationType: str
    createdAt: datetime
    updatedAt: datetime


LLMChatRequest.model_rebuild()
