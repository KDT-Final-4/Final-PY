"""엔드투엔드 글 작성 오케스트레이션 서비스."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
try:
    from langsmith import traceable
except ImportError:  # pragma: no cover - optional
    def traceable(*args, **kwargs):  # type: ignore
        def decorator(fn):
            return fn
        return decorator

from app import config
from app.logs import async_send_log
from app.schemas.llm import LlmSetting
from app.schemas.products import SsadaguProduct
from app.schemas.upload import UploadChannelSettings, UploadRequest
from app.schemas.write import WriteRequest, WriteResponse
from app.services.keywords import KeywordService
from app.services.llm import LLMService
from app.services.promo import PromoService
from app.services.relevance import RelevanceService
from app.services.ssadagu import SsadaguService
from app.services.text_cleaner import try_repair_json
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
        category_llm: Optional[LLMService] = None,
    ):
        self.trends = trends or GoogleTrendsService()
        self.keywords = keywords or KeywordService()
        self.ssadagu = ssadagu or SsadaguService()
        self.relevance = relevance or RelevanceService()
        self.promo = promo or PromoService()
        self.upload = upload or UploadService()
        self.category_llm = category_llm or LLMService()

    @traceable(run_type="chain")
    async def process(self, req: WriteRequest) -> WriteResponse:
        """전체 프로세스를 실행한다. LangGraph가 있으면 그래프, 없으면 순차."""
        upload_channel = _first_channel(req.uploadChannels)
        user_id = _resolve_user_id(req)
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
                "generation_type": req.llmChannel.generationType,
                "upload_channel": upload_channel,
                "llm_setting": req.llmChannel,
                "user_id": user_id,
                "job_id": req.jobId,
                "platform": None,
                "upload_request_builder": _to_upload_request_from_state,
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
        user_id = _resolve_user_id(req)
        keyword = req.keyword
        await _log(
            "INFO",
            "write 프로세스 시작(순차)",
            job_id=job_id,
            user_id=user_id,
            keyword=keyword,
        )
        upload_channel = _first_channel(req.uploadChannels)
        # 1. 키워드 준비 (입력 키워드도 LLM refine 후 사용)
        if keyword:
            refined = await self.keywords.refine(
                [keyword], llm_setting=req.llmChannel, job_id=job_id
            )
            keyword = refined.get("real_keyword") or refined.get("keyword") or keyword
            await _log(
                "INFO",
                "입력 키워드 변환",
                sub=keyword,
                job_id=job_id,
                user_id=user_id,
                keyword=keyword,
            )
        else:
            keywords = await self.trends.fetch_keywords(
                limit=20, headless=True, job_id=job_id
            )
            if not keywords:
                raise RuntimeError("트렌드 키워드 수집 실패")
            refined = await self.keywords.refine(
                keywords, llm_setting=req.llmChannel, job_id=job_id
            )
            keyword = (
                refined.get("real_keyword") or refined.get("keyword") or keywords[0]
            )
            await _log(
                "INFO",
                "트렌드 기반 키워드 선택",
                sub=keyword,
                job_id=job_id,
                user_id=user_id,
                keyword=keyword,
            )

        # 2~4. 상품 검색 및 연관도 확인 (최대 5회)
        attempts = 0
        chosen_product: Optional[SsadaguProduct] = None
        while attempts < MAX_RETRIES:
            attempts += 1
            products = await self.ssadagu.search(
                keyword, max_products=20, headless=True, job_id=job_id
            )
            if not products:
                raise RuntimeError("싸다구 상품을 찾지 못했습니다.")
            product = random.choice(list(products))
            rel = await self.relevance.evaluate(
                keyword, product, llm_setting=req.llmChannel, job_id=job_id
            )
            score = float(rel.get("score", 0.0))
            await _log(
                "INFO",
                "연관도 평가",
                sub=f"score={score}",
                job_id=job_id,
                user_id=user_id,
                keyword=keyword,
            )
            if score >= RELEVANCE_THRESHOLD:
                chosen_product = product
                break
        if chosen_product is None:
            await _log(
                "ERROR",
                "연관된 상품을 찾지 못했습니다.",
                job_id=job_id,
                user_id=user_id,
                keyword=keyword,
            )
            raise RuntimeError("연관된 상품을 찾지 못했습니다.")

        # 5. 홍보글 작성
        platform = _resolve_platform(upload_channel)
        promo = await self.promo.generate(
            chosen_product, platform=platform, llm_setting=req.llmChannel, job_id=job_id
        )
        title = promo.get("title", "").strip()
        body = promo.get("body", "").strip()
        category = await self.classify_category(chosen_product, req.llmChannel)

        # 6. 본문 내 링크를 리디렉트 링크로 치환
        redirect_url = _build_redirect_url(job_id)
        body_replaced = body.replace(str(chosen_product.product_link), redirect_url)

        link_out = ""
        generation_type = req.llmChannel.generationType
        content_generation_type = generation_type or ""
        generation_type_upper = content_generation_type.upper()

        # 7. 업로드 및 컨텐츠 전송
        if generation_type_upper == "AUTO":
            try:
                upload_req = _to_upload_request(
                    req, upload_channel, title, body_replaced, keyword
                )
                upload_res = await self.upload.upload(upload_req)
                link_out = upload_res.link
            except Exception as exc:
                await _log(
                    "ERROR",
                    "업로드 실패",
                    sub=str(exc),
                    job_id=job_id,
                    user_id=user_id,
                    keyword=keyword,
                )
                # 업로드 실패 시 MANUAL 플로우로 전환하여 글 저장만 진행
                content_generation_type = "MANUAL"
                generation_type_upper = content_generation_type.upper()

        # /api/content로 결과 전송
        await _post_content(
            job_id=job_id,
            upload_channel_id=upload_channel.id,
            user_id=user_id,
            title=title,
            body=body_replaced,
            generation_type=content_generation_type,
            link=link_out if generation_type_upper == "AUTO" else "",
            keyword=keyword,
            product=chosen_product,
            category=category,
        )

        await _log(
            "INFO",
            "write 프로세스 완료",
            job_id=job_id,
            user_id=user_id,
            keyword=keyword,
            is_notifiable=True,
        )
        return WriteResponse(
            jobId=job_id,
            keyword=keyword,
            product_title=chosen_product.title,
            link=link_out,
        )

    async def classify_category(
        self, product: SsadaguProduct, llm_setting: LlmSetting | None = None
    ) -> str:
        """카테고리 목록 파일을 읽어 상품 카테고리를 LLM으로 분류."""
        categories = _load_categories()
        return await _classify_category(product, self.category_llm, llm_setting, categories)


def _first_channel(
    upload_channels: list[UploadChannelSettings],
) -> UploadChannelSettings:
    if not upload_channels:
        raise ValueError("uploadChannels 리스트가 비어 있습니다.")
    return upload_channels[0]


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
    return f"{host}/api/link?jobId={job_id}"


def _to_upload_request(
    req: WriteRequest,
    upload_channel: UploadChannelSettings,
    title: str,
    body: str,
    keyword: str,
) -> UploadRequest:
    user_id = _resolve_user_id(req)
    return UploadRequest(
        userId=user_id,
        jobId=req.jobId,
        title=title,
        body=body,
        keyword=keyword,
        **_upload_channel_kwargs(upload_channel),
    )


def _to_upload_request_from_state(
    state: dict[str, Any], title: str, body: str, keyword: str
) -> UploadRequest:
    upload_channel = state.get("upload_channel")
    if upload_channel is None:
        raise ValueError("upload_channel 정보가 없습니다.")
    job_id = state.get("job_id")
    if not job_id:
        raise ValueError("job_id가 필요합니다.")
    user_id = _state_user_id(state)
    return UploadRequest(
        userId=user_id,
        jobId=job_id,
        title=title,
        body=body,
        keyword=keyword,
        **_upload_channel_kwargs(upload_channel),
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
    category: str,
) -> None:
    gen_type_upper = (generation_type or "").upper()
    status = "APPROVED" if gen_type_upper == "AUTO" else "PENDING"
    payload = {
        "jobId": job_id,
        "uploadChannelId": upload_channel_id,
        "userId": user_id,
        "title": title,
        "body": body,
        "status": status,
        "generationType": generation_type,
        "link": link,
        "keyword": keyword,
        "product": {
            "title": product.title,
            "link": str(product.product_link),
            "thumbnail": str(product.thumbnail_link or ""),
            "price": product.price or 0,
            "category": category,
        },
    }
    base = config.get_log_endpoint()
    parsed = urlparse(base)
    host = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{host}/api/content"
    try:
        headers = config.build_internal_headers()
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json=payload,
                timeout=config.get_log_timeout(),
                headers=headers,
        )
    except Exception:
        await _log(
            "WARN",
            "컨텐츠 전송 실패",
            sub=url,
            job_id=job_id,
            user_id=user_id,
            keyword=keyword,
        )


async def classify_category(
    product: SsadaguProduct, llm_setting: LlmSetting | None = None, llm: LLMService | None = None
) -> str:
    """카테고리 목록 파일을 읽어 상품 카테고리를 LLM으로 분류."""
    categories = _load_categories()
    service = llm or LLMService()
    return await _classify_category(product, service, llm_setting, categories)


def _with_keyword(keyword: str | None, sub: str) -> str:
    parts = []
    if keyword:
        parts.append(f"keyword={keyword}")
    if sub:
        if not keyword or sub != keyword:
            parts.append(sub)
    return " | ".join(parts)


async def _log(
    level: str,
    message: str,
    *,
    sub: str = "",
    job_id: str = "",
    user_id: int = 1,
    keyword: str | None = None,
    is_notifiable: bool | None = None,
) -> None:
    submessage = _with_keyword(keyword, sub)
    try:
        await async_send_log(
            level=level,
            message=message,
            submessage=submessage,
            logged_process="write",
            job_id=job_id,
            user_id=user_id,
            is_notifiable=is_notifiable,
        )
    except Exception:
        return


def _resolve_user_id(req: WriteRequest) -> int:
    """요청에서 사용자 ID를 추출한다."""
    try:
        llm_user = getattr(req.llmChannel, "userId", None)  # type: ignore[attr-defined]
        if llm_user:
            return llm_user
    except Exception:
        pass
    if getattr(req, "userId", None):
        return req.userId
    return 1


def _state_user_id(state: dict[str, Any]) -> int:
    """그래프 상태에서 사용자 ID를 추출한다."""
    if state.get("user_id"):
        return state["user_id"]
    llm_setting = state.get("llm_setting")
    try:
        candidate = getattr(llm_setting, "userId", None) or llm_setting.get("userId")  # type: ignore[union-attr]
        if candidate:
            return candidate
    except Exception:
        pass
    return 1


def _upload_channel_kwargs(upload_channel: UploadChannelSettings) -> dict[str, Any]:
    """UploadRequest 생성 시 채널 정보를 납작하게 펼친다."""
    return {
        "channelName": upload_channel.name,
        "naver_login_id": getattr(upload_channel, "naver_login_id", None)
        or getattr(upload_channel, "apiKey", None),
        "naver_login_pw": getattr(upload_channel, "naver_login_pw", None),
        "naver_blog_id": getattr(upload_channel, "naver_blog_id", None),
        "x_consumer_key": getattr(upload_channel, "x_consumer_key", None),
        "x_consumer_secret": getattr(upload_channel, "x_consumer_secret", None),
        "x_access_token": getattr(upload_channel, "x_access_token", None),
        "x_access_token_secret": getattr(upload_channel, "x_access_token_secret", None),
    }


CATEGORY_FILE = Path(__file__).resolve().parent.parent / "prompts" / "categories.txt"


def _load_categories(path: Path = CATEGORY_FILE) -> list[tuple[str, str]]:
    """카테고리 목록을 [id, 설명] 리스트로 읽는다."""
    categories: list[tuple[str, str]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                parts = raw.split(maxsplit=1)
                if not parts:
                    continue
                cat_id = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                categories.append((cat_id, desc))
    except FileNotFoundError:
        return []
    return categories


def _category_prompt(product: SsadaguProduct, categories: list[tuple[str, str]]) -> str:
    lines = "\n".join([f"- {cid}: {desc}" for cid, desc in categories])
    specs = (
        "\n".join([f"- {k}: {v}" for k, v in (product.detail_specs or {}).items()])
        if product.detail_specs
        else "- 없음"
    )
    price_text = f"{product.price}" if product.price is not None else "알 수 없음"
    return f"""상품 정보를 보고 아래 카테고리 중 하나를 골라 JSON(category)로만 알려줘.
카테고리 목록:
{lines}

상품:
- 이름: {product.title}
- 가격: {price_text}
- 링크: {product.product_link}
- 썸네일: {product.thumbnail_link or '없음'}
- 스펙:
{specs}
"""


async def _classify_category(
    product: SsadaguProduct,
    llm: LLMService,
    llm_setting: LlmSetting | None,
    categories: list[tuple[str, str]],
) -> str:
    if not categories:
        return "0"
    system_prompt = "주어진 상품에 가장 적합한 카테고리를 선택하고 JSON으로 반환한다. 출력은 {\"category\": \"카테고리ID\"} 한 개만 포함한다."
    user_input = _category_prompt(product, categories)
    answer = await llm.chat(
        system_prompt=system_prompt,
        user_input=user_input,
        model=llm_setting.modelName if llm_setting else None,
        temperature=llm_setting.temperature if llm_setting else None,
        api_key=llm_setting.apiKey if llm_setting else None,
    )
    cleaned = try_repair_json(answer) or answer
    try:
        parsed = json.loads(cleaned)
        cat = parsed.get("category") or parsed.get("id") or parsed.get("label")
        if isinstance(cat, str) and cat.strip():
            return cat.strip()
    except Exception:
        pass
    # fallback: 첫 번째 카테고리 id
    return categories[0][0]
