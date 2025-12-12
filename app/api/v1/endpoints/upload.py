"""업로드 실행 및 링크 콜백 전송 엔드포인트."""

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app import config
from app.logs import async_send_log
from app.schemas.content import ContentLinkUpdate
from app.schemas.upload import UploadRequest
from app.services.upload import UploadService

router = APIRouter(prefix="/upload", tags=["upload"])


def get_upload_service() -> UploadService:
    return UploadService()


async def _notify_content_link(payload: ContentLinkUpdate) -> None:
    """외부 로그/콜백 서버의 /api/content/link 로 전송."""
    try:
        endpoint = config.get_log_content_link_endpoint()
        url = (
            endpoint
            if endpoint.endswith("/content/link")
            else f"{endpoint}/content/link"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.patch(url, json=payload.model_dump())
            resp.raise_for_status()
    except Exception as exc:  # pragma: no cover
        await async_send_log(
            message="콘텐츠 링크 콜백 실패",
            level="WARN",
            submessage=str(exc),
            logged_process="upload",
            job_id=payload.jobId,
        )


async def _run_upload_and_callback(service: UploadService, body: UploadRequest) -> None:
    """백그라운드에서 업로드 후 콜백 전송."""
    try:
        result = await service.upload(body)
        await _notify_content_link(
            ContentLinkUpdate(jobId=result.jobId, link=result.link)
        )
    except Exception as exc:  # pragma: no cover
        await async_send_log(
            message="업로드 실패",
            level="ERROR",
            submessage=str(exc),
            logged_process="upload",
            job_id=body.jobId,
        )


@router.post(
    "/",
    summary="업로드 실행 (비동기 콜백)",
    description="요청 즉시 200 OK 를 반환하고 업로드/콜백은 백그라운드에서 처리합니다.",
)
async def upload_content(
    body: UploadRequest,
    service: UploadService = Depends(get_upload_service),
):
    """채널에 따라 업로드하고 외부 콜백 서버에 링크를 전달한다(비동기)."""
    asyncio.create_task(_run_upload_and_callback(service, body))
    await async_send_log(
        message="업로드 요청 수락",
        logged_process="upload",
        job_id=body.jobId,
        submessage=f"channel={body.uploadChannels.name}",
    )
    return
