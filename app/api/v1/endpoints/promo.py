"""프로모션 생성 엔드포인트."""

from fastapi import APIRouter, Depends

from app.schemas.promo import PromoRequest, PromoResponse
from app.services.llm import LLMService
from app.services.promo import PromoService

router = APIRouter(prefix="/promo", tags=["promo"])


def get_promo_service() -> PromoService:
    return PromoService()


@router.post("/ssadagu/blog", response_model=PromoResponse, summary="싸다구 상품으로 네이버 블로그 홍보글 생성")
async def create_ssadagu_blog(
    body: PromoRequest,
    service: PromoService = Depends(get_promo_service),
) -> PromoResponse:
    result = await service.generate(
        product=body.product,
        platform=body.platform,
        llm_setting=body.llm_setting,
    )
    return PromoResponse(**result)
