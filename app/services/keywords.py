"""쇼핑몰 검색어 생성 서비스."""

from __future__ import annotations

import json
from typing import Optional

from app.logs import send_log
from app.prompts.keywords import get_system_prompt
from app.schemas.llm import LlmSetting
from app.schemas.trends import GoogleTrendItem
from app.services.llm import LLMService


class KeywordService:
    """트렌드 키워드를 쇼핑몰 검색어로 변형."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    @staticmethod
    def _user_input(trends: list[GoogleTrendItem], extra_prompt: str | None) -> str:
        lines = "\n".join([f"- {item.keyword} (cat:{item.categoryId}, vol:{item.searchVolume})" for item in trends])
        return f"""트렌드 키워드 목록:
{lines}
추가 지시문(선택): {extra_prompt or '없음'}
위 목록 중에서 쇼핑몰 검색에 가장 적합한 keyword를 하나 고르고, real_keyword(필요 시 변형), reason을 JSON으로 반환."""

    async def refine(
        self,
        trends: list[GoogleTrendItem],
        *,
        llm_setting: LlmSetting | None = None,
    ) -> dict[str, str]:
        extra_prompt = llm_setting.prompt if llm_setting else None
        system_prompt = get_system_prompt()
        user_input = self._user_input(trends, extra_prompt)

        send_log(
            message="트렌드 키워드 → 검색어 변환 시작",
            submessage=f"count={len(trends)}",
            logged_process="keywords",
        )
        answer = await self.llm.chat(
            system_prompt=system_prompt,
            user_input=user_input,
            model=llm_setting.modelName if llm_setting else None,
            temperature=llm_setting.temperature if llm_setting else None,
            api_key=llm_setting.apiKey if llm_setting else None,
        )

        default_keyword = trends[0].keyword if trends else ""
        real_keyword = default_keyword
        reason = answer.strip()
        try:
            parsed = json.loads(answer)
            real_keyword = parsed.get("real_keyword") or parsed.get("keyword") or real_keyword
            reason = parsed.get("reason", reason) or reason
            keyword_out = parsed.get("keyword", default_keyword) or default_keyword
        except Exception:
            keyword_out = default_keyword

        send_log(
            message="트렌드 키워드 → 검색어 변환 완료",
            submessage=f"keyword={keyword_out}, real={real_keyword}",
            logged_process="keywords",
        )
        return {
            "keyword": keyword_out,
            "real_keyword": real_keyword,
            "reason": reason.strip(),
        }
