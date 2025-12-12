"""LangGraph 기반 글 작성 오케스트레이션 그래프."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from langsmith import traceable

from app import config
from app.logs import async_send_log
from app.schemas.products import SsadaguProduct

# LangGraph는 선택적 의존성. 설치되지 않았으면 ImportError를 던진다.
try:
    from langgraph.graph import END, StateGraph
except ImportError as exc:  # pragma: no cover - 설치 안 된 경우
    StateGraph = None  # type: ignore
    END = None  # type: ignore
    _import_error = exc
else:
    _import_error = None


def build_write_graph(
    services, *, max_retries: int = 5, relevance_threshold: float = 0.8
):
    """LangGraph로 노드 흐름을 구성해 컴파일된 그래프를 반환한다."""
    if _import_error:
        raise _import_error

    graph = StateGraph(dict)

    @traceable(run_type="tool")
    async def log(level: str, msg: str, sub: str = "", job_id: str = ""):
        try:
            await async_send_log(
                level=level,
                message=msg,
                submessage=sub,
                logged_process="write",
                job_id=job_id,
            )
        except Exception:
            return

    @traceable(run_type="chain")
    async def prepare_keyword(state: Dict[str, Any]) -> Dict[str, Any]:
        job_id = state.get("job_id", "")
        keyword = state.get("keyword")
        if keyword:
            await log("INFO", "키워드 입력 사용", keyword, job_id)
            return state
        trends = await services.trends.fetch_keywords(limit=20, headless=True)
        if not trends:
            raise RuntimeError("트렌드 키워드 수집 실패")
        refined = await services.keywords.refine(
            trends, llm_setting=state["llm_setting"]
        )
        keyword = refined.get("real_keyword") or refined.get("keyword") or trends[0]
        await log("INFO", "트렌드 기반 키워드 선택", keyword, job_id)
        state["keyword"] = keyword
        return state

    @traceable(run_type="chain")
    async def fetch_products(state: Dict[str, Any]) -> Dict[str, Any]:
        keyword = state["keyword"]
        products = await services.ssadagu.search(
            keyword, max_products=20, headless=True
        )
        if not products:
            raise RuntimeError("싸다구 상품을 찾지 못했습니다.")
        state["products"] = list(products)
        return state

    @traceable(run_type="chain")
    async def choose_product(state: Dict[str, Any]) -> Dict[str, Any]:
        products = state.get("products") or []
        state["product"] = random.choice(products)
        return state

    @traceable(run_type="chain")
    async def evaluate(state: Dict[str, Any]) -> Dict[str, Any]:
        job_id = state.get("job_id", "")
        keyword = state["keyword"]
        product: SsadaguProduct = state["product"]
        rel = await services.relevance.evaluate(
            keyword, product, llm_setting=state["llm_setting"]
        )
        score = float(rel.get("score", 0.0))
        await log("INFO", "연관도 평가", f"score={score}", job_id)
        state["relevance_score"] = score
        return state

    @traceable(run_type="router")
    def route_after_eval(state: Dict[str, Any]) -> str:
        score = state.get("relevance_score", 0.0)
        retries = state.get("retries", 0)
        if score >= relevance_threshold:
            return "generate"
        if retries + 1 >= max_retries:
            return "fail"
        state["retries"] = retries + 1
        return "retry"

    @traceable(run_type="chain")
    async def generate(state: Dict[str, Any]) -> Dict[str, Any]:
        product: SsadaguProduct = state["product"]
        platform = state.get("platform") or _resolve_platform(
            state["upload_channel"].name
        )
        promo = await services.promo.generate(
            product, platform=platform, llm_setting=state["llm_setting"]
        )
        title = promo.get("title", "").strip()
        body = promo.get("body", "").strip()
        redirect_url = _build_redirect_url(state["job_id"])
        body = body.replace(str(product.product_link), redirect_url)
        state["title"] = title
        state["body"] = body
        return state

    @traceable(run_type="chain")
    async def upload_if_auto(state: Dict[str, Any]) -> Dict[str, Any]:
        gen_type = (state.get("generation_type") or "").upper()
        if gen_type != "AUTO":
            state["link"] = ""
            return state
        upload_req = state["upload_request_builder"](
            state, state["title"], state["body"], state["keyword"]
        )
        upload_res = await services.upload.upload(upload_req)
        state["link"] = upload_res.link
        return state

    @traceable(run_type="chain")
    async def finalize(state: Dict[str, Any]) -> Dict[str, Any]:
        product: SsadaguProduct = state["product"]
        await _post_content(
            job_id=state["job_id"],
            upload_channel_id=state["upload_channel"].id,
            user_id=state["user_id"],
            title=state["title"],
            body=state["body"],
            generation_type=state["generation_type"],
            link=(
                state.get("link", "")
                if (state.get("generation_type") or "").upper() == "AUTO"
                else ""
            ),
            keyword=state["keyword"],
            product=product,
        )
        return state

    @traceable(run_type="chain")
    async def fail(state: Dict[str, Any]) -> Dict[str, Any]:
        job_id = state.get("job_id", "")
        await log("ERROR", "연관된 상품을 찾지 못했습니다.", job_id=job_id)
        raise RuntimeError("연관된 상품을 찾지 못했습니다.")

    graph.add_node("prepare_keyword", prepare_keyword)
    graph.add_node("fetch_products", fetch_products)
    graph.add_node("choose_product", choose_product)
    graph.add_node("evaluate", evaluate)
    graph.add_node("generate", generate)
    graph.add_node("upload", upload_if_auto)
    graph.add_node("finalize", finalize)
    graph.add_node("fail", fail)

    graph.set_entry_point("prepare_keyword")
    graph.add_edge("prepare_keyword", "fetch_products")
    graph.add_edge("fetch_products", "choose_product")
    graph.add_edge("choose_product", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {
            "generate": "generate",
            "retry": "fetch_products",
            "fail": "fail",
        },
    )
    graph.add_edge("generate", "upload")
    graph.add_edge("upload", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def _resolve_platform(name: str) -> str:
    name_low = (name or "").lower()
    if "naver" in name_low:
        return "naver_blog"
    if name_low in {"x", "twitter"}:
        return "x"
    return name_low or "naver_blog"


def _build_redirect_url(job_id: str) -> str:
    base = config.get_log_endpoint()
    parsed = urlparse(base)
    host = f"{parsed.scheme}://{parsed.netloc}"
    return f"{host}/api/link?jobId={job_id}"


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
        try:
            await async_send_log(
                level="WARN",
                message="컨텐츠 전송 실패",
                submessage=url,
                logged_process="write",
                job_id=job_id,
            )
        except Exception:
            return
