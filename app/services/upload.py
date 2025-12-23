"""업로드 오케스트레이션 서비스."""

from __future__ import annotations

from app import config
from app.logs import async_send_log
from app.schemas.upload import UploadRequest, UploadResponse
from app.services.naver_blog import NaverBlogService
from app.services.x_post import XPostService


class UploadService:
    """채널별 업로드 라우팅."""

    def __init__(
        self,
        naver_service: NaverBlogService | None = None,
        x_service: XPostService | None = None,
    ):
        self.naver_service = naver_service or NaverBlogService()
        self.x_service = x_service or XPostService()

    async def upload(self, payload: UploadRequest) -> UploadResponse:
        channel = self._resolve_channel(payload)
        job_id = payload.jobId

        await async_send_log(
            message="업로드 시작",
            submessage=f"channel={channel}",
            logged_process="upload",
            job_id=job_id,
        )

        if channel.startswith("naver"):
            link = await self._upload_naver(payload)
        elif channel in {"x", "twitter"}:
            link = await self._upload_x(payload, job_id=job_id)
        else:
            await async_send_log(
                message="지원하지 않는 채널",
                level="ERROR",
                submessage=channel,
                logged_process="upload",
                job_id=job_id,
            )
            raise ValueError(f"지원하지 않는 채널: {channel}")

        await async_send_log(
            message="업로드 완료",
            logged_process="upload",
            submessage=f"channel={channel}",
            job_id=job_id,
            is_notifiable=True,
        )

        return UploadResponse(jobId=job_id, link=link, channel=channel)

    def _resolve_channel(self, payload: UploadRequest) -> str:
        return (payload.channelName or "unknown").strip().lower()

    async def _upload_naver(self, payload: UploadRequest) -> str:
        print(payload.client_id)
        login_id = payload.client_id or config.get_naver_login_id()
        login_pw = payload.client_pw or config.get_naver_login_pw()
        blog_id = payload.naver_blog_id or payload.client_id or config.get_naver_blog_id() or login_id

        if not login_id or not login_pw:
            raise ValueError("네이버 로그인 정보가 없습니다.")

        result = await self.naver_service.publish(
            login_id=login_id,
            login_pw=login_pw,
            title=payload.title,
            content=payload.body,
            blog_id=blog_id,
            job_id=payload.jobId,
        )
        if not result.success or not result.url:
            raise RuntimeError(f"네이버 업로드 실패: {result.message}")
        return result.url

    async def _upload_x(self, payload: UploadRequest, *, job_id: str | None = None) -> str:
        return await self.x_service.post_async(
            title=payload.title,
            content=payload.body,
            consumer_key=payload.x_consumer_key,
            consumer_secret=payload.x_consumer_secret,
            access_token=payload.x_access_token,
            access_token_secret=payload.x_access_token_secret,
            job_id=job_id,
        )
