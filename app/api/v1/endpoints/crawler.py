"""콜백 지향 구글 트렌드 크롤러 엔드포인트."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends

from app import config
from app.logs import async_send_log
from app.services.trends import GoogleTrendsService

router = APIRouter(prefix="/crawler", tags=["crawler"])


def get_trends_service() -> GoogleTrendsService:
    """Provide a trends service instance."""
    return GoogleTrendsService()


async def _post_trend_callback(payload: list[dict]) -> None:
    """콜백 서버(/api/trend)로 결과를 전송한다."""
    endpoint = config.get_log_trend_endpoint()
    timeout = config.get_log_timeout()
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()


async def _run_crawl_and_callback(
    service: GoogleTrendsService, limit: int, headless: bool
) -> None:
    """백그라운드에서 크롤링 후 콜백 전송."""
    try:
        await async_send_log(
            message="트렌드 크롤러 백그라운드 시작",
            level="INFO",
            submessage=f"limit={limit}",
            logged_process="crawler",
        )
        items = await service.fetch_google_crawler_response(
            limit=limit, headless=headless
        )
        payload = [
            {
                "categoryId": item.categoryId or 0,
                "keyword": item.keyword,
                "searchVolume": item.searchVolume or 0,
                "snsType": (item.snsType or "GOOGLE").upper(),
            }
            for item in items
        ]
        await _post_trend_callback(payload)
        await async_send_log(
            message="트렌드 콜백 전송 완료",
            level="INFO",
            submessage=f"count={len(payload)}",
            logged_process="crawler",
        )
    except Exception as exc:  # pragma: no cover - 네트워크/콜백 실패
        await async_send_log(
            message="트렌드 콜백 전송 실패",
            level="ERROR",
            submessage=str(exc),
            logged_process="crawler",
        )


@router.get(
    "",
    summary="구글 트렌드 크롤링 후 콜백(/api/trend)으로 전달",
    description=(
        "구글 트렌드 키워드를 크롤링한 뒤 결과를 LOG 서버의 /api/trend로 전송합니다. "
        "호출 즉시 OK를 반환하며, 실제 크롤링/콜백은 백그라운드에서 진행됩니다. "
        "진행 상황은 로그 서버에서 확인하세요."
    ),
)
async def crawl_and_callback(
    limit: int = 20,
    headless: bool = True,
    service: GoogleTrendsService = Depends(get_trends_service),
):
    # 호출 즉시 OK 반환
    asyncio.create_task(_run_crawl_and_callback(service, limit, headless))
    await async_send_log(
        message="트렌드 크롤러 요청 수락",
        level="INFO",
        submessage=f"limit={limit}",
        logged_process="crawler",
    )
    return
