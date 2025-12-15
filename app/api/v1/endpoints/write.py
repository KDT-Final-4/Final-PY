"""글 작성 오케스트레이션 엔드포인트 (/api/write)."""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.logs import async_send_log
from app.schemas.write import WriteRequest, WriteResponse
from app.services.write import WriteService

router = APIRouter(prefix="/write", tags=["write"])


def get_write_service() -> WriteService:
    return WriteService()


async def _run_write(service: WriteService, body: WriteRequest) -> None:
    try:
        await service.process(body)
    except Exception as exc:  # pragma: no cover - 백그라운드 실패는 로그만
        try:
            user_id = getattr(body.llmChannel, "userId", None) or body.userId
        except Exception:
            user_id = body.userId
        await async_send_log(
            level="ERROR",
            message="write 프로세스 실패",
            submessage=str(exc),
            logged_process="write",
            job_id=body.jobId,
            user_id=user_id,
        )


@router.post(
    "/",
    response_model=None,
    summary="글 작성 + 업로드 오케스트레이션 (콜백형)",
    description="요청 즉시 200 OK를 반환하고 내부에서 비동기로 처리합니다.",
)
async def write_content(
    body: WriteRequest,
    service: WriteService = Depends(get_write_service),
) -> Response:
    """키워드 선정 → 상품 크롤링 → 홍보글 생성 → (선택적) 업로드를 수행한다. 즉시 OK 반환."""
    asyncio.create_task(_run_write(service, body))
    return Response(status_code=status.HTTP_200_OK)
