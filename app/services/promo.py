"""프로모션 생성 서비스."""

from __future__ import annotations

import json
from typing import Optional

from app.logs import async_send_log
from app.prompts.promo import get_platform_guide
from app.schemas.llm import LlmSetting
from app.schemas.products import SsadaguProduct
from app.services.llm import LLMService


class PromoService:
    """싸다구 상품 기반 홍보글 생성 서비스 (네이버 블로그/X 확장 가능)."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    @staticmethod
    def _build_system_prompt(platform: str) -> str:
        guide = get_platform_guide(platform)
        return f"""너는 이커머스 마케터다.
플랫폼: {platform}
아래 가이드에 따라 홍보글을 작성한다.
{guide}
출력은 JSON 형식으로 title, body만 포함한다."""

    @staticmethod
    def _build_user_input(product: SsadaguProduct, extra_prompt: str | None) -> str:
        specs = (
            "\n".join([f"- {k}: {v}" for k, v in (product.detail_specs or {}).items()])
            if product.detail_specs
            else "- 없음"
        )
        price_text = f"{product.price}" if product.price is not None else "알 수 없음"
        user = f"""상품 정보:
- 이름: {product.title}
- 가격: {price_text}
- 링크: {product.product_link}
- 썸네일: {product.thumbnail_link or '없음'}
- 스펙:
{specs}

추가 지시문(선택): {extra_prompt or '없음'}
위 정보를 반영해 JSON(title, body)만 반환해줘."""
        return user

    async def generate(
        self,
        product: SsadaguProduct,
        *,
        platform: str = "naver_blog",
        llm_setting: LlmSetting | None = None,
    ) -> dict[str, str]:
        """플랫폼에 맞는 홍보글 JSON(title, body)을 생성."""
        extra_prompt = llm_setting.prompt if llm_setting else None
        system_prompt = self._build_system_prompt(platform)
        user_input = self._build_user_input(product, extra_prompt)

        await send_log_async_safe(
            message="프로모션 생성 시작",
            submessage=f"platform={platform}, product={product.title}",
            logged_process="promo",
        )
        answer = await self.llm.chat(
            system_prompt=system_prompt,
            user_input=user_input,
            model=llm_setting.modelName if llm_setting else None,
            temperature=llm_setting.temperature if llm_setting else None,
            api_key=llm_setting.apiKey if llm_setting else None,
        )

        try:
            parsed = json.loads(answer)
            title = parsed.get("title") or ""
            body = parsed.get("body") or ""
        except Exception:
            # LLM이 JSON 형식이 아닐 경우 대비하여 fallback
            title, body = "", answer.strip()

        await send_log_async_safe(
            message="프로모션 생성 완료",
            submessage=f"platform={platform}, title={title}",
            logged_process="promo",
        )
        return {
            "title": title.strip(),
            "body": body.strip(),
            "link": str(product.product_link),
            "platform": platform,
        }
async def send_log_async_safe(**kwargs) -> None:
    try:
        await async_send_log(**kwargs)
    except Exception:
        return
