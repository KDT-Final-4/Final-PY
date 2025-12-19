"""Service for Ssadagu crawling."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from typing import Optional
from urllib.parse import quote

try:
    from playwright.async_api import Browser, Page, async_playwright
except ImportError:  # pragma: no cover - optional dependency for tests
    Browser = Page = None  # type: ignore
    async_playwright = None  # type: ignore

from app.logs import async_send_log
from app.schemas.products import SsadaguProduct

SSADAGU_SEARCH_URL = "https://ssadagu.kr/shop/search.php?ss_tx={query}"
SSADAGU_BASE_URL = "https://ssadagu.kr"


def _build_search_url(keyword: str) -> str:
    return SSADAGU_SEARCH_URL.format(query=quote(keyword))


def _parse_price(price_text: str) -> Optional[float]:
    """가격 문자열에서 숫자만 추출해 float 변환."""
    digits = re.sub(r"[^\d]", "", price_text or "")
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


async def _extract_detail_specs(detail_page: Page) -> dict[str, str]:
    """상세 페이지에서 스펙을 키-값으로 수집한다."""
    specs: dict[str, str] = {}
    container = await detail_page.query_selector("div.pro-info-boxs") or await detail_page.query_selector(
        "#productAttributes"
    )
    if not container:
        return specs

    items = await container.query_selector_all("div.pro-info-item")
    for item in items:
        try:
            title_elem = await item.query_selector("div.pro-info-title") or await item.query_selector(
                "div[class*='pro-info-title']"
            )
            value_elem = await item.query_selector("div.pro-info-info") or await item.query_selector(
                "div[class*='pro-info-info']"
            )
            if not title_elem or not value_elem:
                continue
            title = (await title_elem.inner_text() or "").strip().rstrip(":")
            value = (await value_elem.inner_text() or "").strip()
            if title and value:
                specs[title] = value
        except Exception:
            continue

    return specs


async def _extract_price_from_detail(detail_page: Page) -> Optional[float]:
    selectors = [
        "div.item-info div.item-info-base div.flex-container div.flex-container h3.pdt_price span.price.gsItemPriceKWR",
        "div.item-info div.item-info-base h3.pdt_price span.price",
        "div.item-info-base .pdt_price span[class*='price']",
        "span.price.gsItemPriceKWR",
        ".pdt_price span.price",
    ]
    for selector in selectors:
        try:
            elem = await detail_page.query_selector(selector)
            if not elem:
                continue
            text = (await elem.inner_text() or "").strip()
            price = _parse_price(text)
            if price is not None:
                return price
        except Exception:
            continue
    return None


class SsadaguService:
    """싸다구 쇼핑몰 크롤링 서비스."""

    async def search(
        self,
        keyword: str,
        *,
        max_products: int = 20,
        headless: bool = True,
        page_timeout_ms: int = 30_000,
        job_id: str | None = None,
    ) -> Sequence[SsadaguProduct]:
        """검색 키워드로 싸다구 상품을 크롤링한다."""
        if async_playwright is None:
            raise ImportError("playwright 패키지가 필요합니다.")
        search_url = _build_search_url(keyword)
        products: list[SsadaguProduct] = []

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            try:
                await _log_async("INFO", f"싸다구 검색 시작: {keyword}", job_id=job_id)
                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=page_timeout_ms)
                except Exception:
                    await page.goto(search_url, wait_until="load", timeout=page_timeout_ms)

                await page.wait_for_timeout(2_000)
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(0.5)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)

                product_list = await page.query_selector("ul.search_product_list") or await page.query_selector(
                    "#div_product_list"
                )
                if not product_list:
                    return []

                items = await product_list.query_selector_all("li")
                for idx, item_elem in enumerate(items):
                    if len(products) >= max_products:
                        break
                    try:
                        title = (await item_elem.get_attribute("data-title") or "").strip()
                        thumbnail = (await item_elem.get_attribute("data-img-url") or "").strip() or None

                        link = ""
                        link_elem = await item_elem.query_selector("a")
                        if link_elem:
                            href = (await link_elem.get_attribute("href") or "").strip()
                            if href:
                                link = href if href.startswith("http") else f"{SSADAGU_BASE_URL}{href}"

                        if not title or not link:
                            continue

                        price: Optional[float] = None
                        detail_specs: dict[str, str] = {}

                        detail_page = None
                        try:
                            detail_page = await browser.new_page()
                            await detail_page.goto(
                                link, wait_until="domcontentloaded", timeout=page_timeout_ms
                            )
                            await detail_page.wait_for_timeout(1_000 + (idx % 3) * 300)
                            price = await _extract_price_from_detail(detail_page)
                            detail_specs = await _extract_detail_specs(detail_page)
                        except Exception as exc:  # pragma: no cover - 네트워크 환경 의존
                            await _log_async("WARN", f"상세 정보 추출 실패 {link} | {exc}", job_id=job_id)
                        finally:
                            if detail_page:
                                try:
                                    await detail_page.close()
                                except Exception:
                                    pass

                        products.append(
                            SsadaguProduct(
                                title=title,
                                price=price,
                                product_link=link,
                                thumbnail_link=thumbnail,
                                detail_specs=detail_specs,
                            )
                        )
                    except Exception as exc:  # pragma: no cover - 네트워크 환경 의존
                        await _log_async("WARN", f"상품 파싱 실패: {exc}", job_id=job_id)
                        continue
            finally:
                await browser.close()

        await _log_async("INFO", f"싸다구 검색 완료: {keyword}, count={len(products)}", job_id=job_id)
        return products


async def _log_async(level: str, message: str, job_id: str | None = None) -> None:
    try:
        await async_send_log(
            message=message,
            level=level,
            logged_process="ssadagu",
            job_id=job_id or "",
        )
    except Exception:
        return
