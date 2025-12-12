"""쇼핑몰 검색어 생성 엔드포인트."""

from fastapi import APIRouter, Depends

from app.schemas.keywords import KeywordRefineRequest, KeywordRefineResponse
from app.services.keywords import KeywordService

router = APIRouter(prefix="/keywords", tags=["keywords"])


def get_keyword_service() -> KeywordService:
    return KeywordService()


@router.post("/refine", response_model=KeywordRefineResponse, summary="트렌드 키워드 → 쇼핑몰 검색어 변환")
async def refine_keyword(
    body: KeywordRefineRequest,
    service: KeywordService = Depends(get_keyword_service),
) -> KeywordRefineResponse:
    result = await service.refine(trends=body.google_trends, llm_setting=body.llm_setting)
    return KeywordRefineResponse(**result)
