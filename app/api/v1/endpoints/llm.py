"""LLM 호출 엔드포인트."""

from fastapi import APIRouter, Depends

from app.schemas.llm import LLMChatRequest, LLMChatResponse, LlmSetting
from app.services.llm import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_service() -> LLMService:
    return LLMService()


@router.post("/chat", response_model=LLMChatResponse, summary="시스템 프롬프트 + 입력 → 답변 생성")
async def chat(
    body: LLMChatRequest,
    service: LLMService = Depends(get_llm_service),
) -> LLMChatResponse:
    setting: LlmSetting | None = body.llm_setting
    system_prompt = body.system_prompt or (setting.prompt if setting else "")
    model = setting.modelName if setting else None
    temperature = setting.temperature if setting else None
    api_key = setting.apiKey if setting else None

    answer = await service.chat(
        system_prompt,
        body.user_input,
        model=model,
        temperature=temperature,
        api_key=api_key,
    )
    return LLMChatResponse(answer=answer)
