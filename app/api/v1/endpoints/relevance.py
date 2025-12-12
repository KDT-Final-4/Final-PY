"""키워드-상품 연관도 평가 엔드포인트."""

from fastapi import APIRouter, Depends

from app.schemas.relevance import RelevanceRequest, RelevanceResponse
from app.services.relevance import RelevanceService

router = APIRouter(prefix="/relevance", tags=["relevance"])


def get_relevance_service() -> RelevanceService:
    return RelevanceService()


@router.post("/ssadagu", response_model=RelevanceResponse, summary="키워드-싸다구 상품 연관도 평가")
async def evaluate_relevance(
    body: RelevanceRequest,
    service: RelevanceService = Depends(get_relevance_service),
) -> RelevanceResponse:
    result = await service.evaluate(
        keyword=body.keyword,
        product=body.product,
        llm_setting=body.llm_setting,
    )
    return RelevanceResponse(**result)
