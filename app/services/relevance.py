"""키워드-상품 연관도 평가 서비스."""

from __future__ import annotations

import json
from typing import Optional

from app.logs import async_send_log
from app.prompts.relevance import get_system_prompt
from app.schemas.llm import LlmSetting
from app.schemas.products import SsadaguProduct
from app.services.llm import LLMService
from app.services.text_cleaner import try_repair_json


class RelevanceService:
    """LLM을 이용해 키워드-상품 연관도 점수를 산출한다."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    @staticmethod
    def _user_input(keyword: str, product: SsadaguProduct, extra_prompt: str | None) -> str:
        specs = (
            "\n".join([f"- {k}: {v}" for k, v in (product.detail_specs or {}).items()])
            if product.detail_specs
            else "- 없음"
        )
        price_text = f"{product.price}" if product.price is not None else "알 수 없음"
        return f"""키워드: {keyword}

상품:
- 이름: {product.title}
- 가격: {price_text}
- 링크: {product.product_link}
- 썸네일: {product.thumbnail_link or '없음'}
- 스펙:
{specs}

추가 지시문(선택): {extra_prompt or '없음'}
위 정보를 바탕으로 JSON(score, reason)만 반환."""

    async def evaluate(
        self,
        keyword: str,
        product: SsadaguProduct,
        *,
        llm_setting: LlmSetting | None = None,
    ) -> dict[str, str | float]:
        extra_prompt = llm_setting.prompt if llm_setting else None
        system_prompt = get_system_prompt()
        user_input = self._user_input(keyword, product, extra_prompt)

        await send_log_async_safe(
            message="키워드-상품 연관도 평가 시작",
            submessage=f"keyword={keyword}",
            logged_process="relevance",
        )
        answer = await self.llm.chat(
            system_prompt=system_prompt,
            user_input=user_input,
            model=llm_setting.modelName if llm_setting else None,
            temperature=llm_setting.temperature if llm_setting else None,
            api_key=llm_setting.apiKey if llm_setting else None,
        )
        cleaned_answer = try_repair_json(answer) or answer

        score = 0.0
        reason = cleaned_answer.strip()
        try:
            parsed = json.loads(cleaned_answer)
            score = float(parsed.get("score", 0.0))
            reason = str(parsed.get("reason", "")).strip() or reason
        except Exception:
            # fallback: keep default score 0.0, use raw answer as reason
            pass

        # 점수 범위 보정
        if score < 0.0:
            score = 0.0
        if score > 1.0:
            score = 1.0

        await send_log_async_safe(
            message="키워드-상품 연관도 평가 완료",
            submessage=f"keyword={keyword} | score={score} | reason={reason}",
            logged_process="relevance",
        )
        return {
            "keyword": keyword,
            "product_title": product.title,
            "score": score,
            "reason": reason,
        }
async def send_log_async_safe(**kwargs) -> None:
    try:
        await async_send_log(**kwargs)
    except Exception:
        return
