"""엔드투엔드 글 작성 오케스트레이션 서비스."""

from __future__ import annotations

import random
from typing import Optional
from urllib.parse import urlparse

import httpx
from langsmith import traceable

from app import config
from app.logs import async_send_log
from app.schemas.products import SsadaguProduct
from app.schemas.upload import UploadChannelSettings, UploadRequest
from app.schemas.write import WriteRequest, WriteResponse
from app.services.keywords import KeywordService
from app.services.promo import PromoService
from app.services.relevance import RelevanceService
from app.services.ssadagu import SsadaguService
from app.services.trends import GoogleTrendsService
from app.services.upload import UploadService

RELEVANCE_THRESHOLD = 0.8
MAX_RETRIES = 5


class WriteService:
    """LangGraph 노드들을 묶어 글 작성/업로드를 수행한다."""

    def __init__(
        self,
        *,
        trends: Optional[GoogleTrendsService] = None,
        keywords: Optional[KeywordService] = None,
        ssadagu: Optional[SsadaguService] = None,
        relevance: Optional[RelevanceService] = None,
        promo: Optional[PromoService] = None,
        upload: Optional[UploadService] = None,
    ):
        self.trends = trends or GoogleTrendsService()
        self.keywords = keywords or KeywordService()
        self.ssadagu = ssadagu or SsadaguService()
        self.relevance = relevance or RelevanceService()
        self.promo = promo or PromoService()
        self.upload = upload or UploadService()

    @traceable(run_type="chain")
    async def process(self, req: WriteRequest) -> WriteResponse:
        """전체 프로세스를 실행한다. LangGraph가 있으면 그래프, 없으면 순차."""
        try:
            from app.flows.write_graph import build_write_graph

            graph = build_write_graph(
                self,
                max_retries=MAX_RETRIES,
                relevance_threshold=RELEVANCE_THRESHOLD,
            )
            initial = {
                "keyword": req.keyword,
                "retries": 0,
                "generation_type": req.llmSettings.generationType,
                "upload_channel": req.uploadChannels,
                "llm_setting": req.llmSettings,
                "user_id": req.userId,
                "job_id": req.jobId,
                "platform": None,
                "upload_request_builder": _to_upload_request,
            }
            state = await graph.ainvoke(initial)
            chosen_product: SsadaguProduct = state["product"]
            return WriteResponse(
                jobId=req.jobId,
                keyword=state["keyword"],
                product_title=chosen_product.title,
                link=state.get("link", ""),
            )
        except ImportError:
            return await self._process_sequential(req)

    @traceable(run_type="chain")
    async def _process_sequential(self, req: WriteRequest) -> WriteResponse:
        """LangGraph 미사용 시 순차 실행."""
        job_id = req.jobId
        await _log("INFO", "write 프로세스 시작(순차)", job_id=job_id)

        keyword = req.keyword
        # 1. 키워드 준비
        if not keyword:
            keywords = await self.trends.fetch_keywords(limit=20, headless=True)
            if not keywords:
                raise RuntimeError("트렌드 키워드 수집 실패")
            refined = await self.keywords.refine(keywords, llm_setting=req.llmSettings)
            keyword = refined.get("real_keyword") or refined.get("keyword") or keywords[0]
            await _log("INFO", "트렌드 기반 키워드 선택", sub=keyword, job_id=job_id)

        # 2~4. 상품 검색 및 연관도 확인 (최대 5회)
        attempts = 0
        chosen_product: Optional[SsadaguProduct] = None
        while attempts < MAX_RETRIES:
            attempts += 1
            products = await self.ssadagu.search(keyword, max_products=20, headless=True)
            if not products:
                raise RuntimeError("싸다구 상품을 찾지 못했습니다.")
            product = random.choice(list(products))
            rel = await self.relevance.evaluate(keyword, product, llm_setting=req.llmSettings)
            score = float(rel.get("score", 0.0))
            await _log("INFO", "연관도 평가", sub=f"score={score}", job_id=job_id)
            if score >= RELEVANCE_THRESHOLD:
                chosen_product = product
                break
        if chosen_product is None:
            await _log("ERROR", "연관된 상품을 찾지 못했습니다.", job_id=job_id)
            raise RuntimeError("연관된 상품을 찾지 못했습니다.")

        # 5. 홍보글 작성
        platform = _resolve_platform(req.uploadChannels)
        promo = await self.promo.generate(
            chosen_product, platform=platform, llm_setting=req.llmSettings
        )
        title = promo.get("title", "").strip()
        body = promo.get("body", "").strip()

        # 6. 본문 내 링크를 리디렉트 링크로 치환
        redirect_url = _build_redirect_url(job_id)
        body_replaced = body.replace(str(chosen_product.product_link), redirect_url)

        link_out = ""
        generation_type = req.llmSettings.generationType
        generation_type_upper = generation_type.upper() if generation_type else ""

        # 7. 업로드 및 컨텐츠 전송
        if generation_type_upper == "AUTO":
            try:
                upload_req = _to_upload_request(req, title, body_replaced, keyword)
                upload_res = await self.upload.upload(upload_req)
                link_out = upload_res.link
            except Exception as exc:
                await _log("ERROR", "업로드 실패", sub=str(exc), job_id=job_id)
                raise

        # /api/content로 결과 전송
        await _post_content(
            job_id=job_id,
            upload_channel_id=req.uploadChannels.id,
            user_id=req.userId,
            title=title,
            body=body_replaced,
            generation_type=generation_type,
            link=link_out if generation_type_upper == "AUTO" else "",
            keyword=keyword,
            product=chosen_product,
        )

        await _log("INFO", "write 프로세스 완료", job_id=job_id)
        return WriteResponse(
            jobId=job_id,
            keyword=keyword,
            product_title=chosen_product.title,
            link=link_out,
        )


def _resolve_platform(ch: UploadChannelSettings) -> str:
    name = (ch.name or "").lower()
    if "naver" in name:
        return "naver_blog"
    if name in {"x", "twitter"}:
        return "x"
    return name or "naver_blog"


def _build_redirect_url(job_id: str) -> str:
    base = config.get_log_endpoint()
    parsed = urlparse(base)
    host = f"{parsed.scheme}://{parsed.netloc}"
    return f"{host}/redirect?id={job_id}"


def _to_upload_request(req: WriteRequest, title: str, body: str, keyword: str) -> UploadRequest:
    return UploadRequest(
        userId=req.userId,
        jobId=req.jobId,
        title=title,
        body=body,
        keyword=keyword,
        uploadChannels=req.uploadChannels,
    )


@traceable(run_type="tool")
async def _post_content(
    *,
    job_id: str,
    upload_channel_id: int,
    user_id: int,
    title: str,
    body: str,
    generation_type: str,
    link: str,
    keyword: str,
    product: SsadaguProduct,
) -> None:
    payload = {
        "jobId": job_id,
        "uploadChannelId": upload_channel_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "status": "PENDING",
        "generationType": generation_type,
        "link": link,
        "keyword": keyword,
        "product": {
            "title": product.title,
            "link": str(product.product_link),
            "thumbnail": str(product.thumbnail_link or ""),
            "price": product.price or 0,
            "category": "",
        },
    }
    base = config.get_log_endpoint()
    parsed = urlparse(base)
    host = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{host}/api/content"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=config.get_log_timeout())
    except Exception:
        await _log("WARN", "컨텐츠 전송 실패", sub=url, job_id=job_id)


async def _log(level: str, message: str, *, sub: str = "", job_id: str = "") -> None:
    try:
        await async_send_log(
            level=level,
            message=message,
            submessage=sub,
            logged_process="write",
            job_id=job_id,
        )
    except Exception:
        return
