"""Service for fetching Google Trends keywords."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import Optional, Set

from playwright.async_api import Page, async_playwright
from pydantic import ValidationError

from app.logs import async_send_log, send_log
from app.schemas.trends import GoogleCrawlerResponse, GoogleTrendItem

TREND_URL = "https://trends.google.co.kr/trending?geo=KR"
EXCLUDED_TEXTS: Set[str] = {
    "Trends",
    "트렌드 상태",
    "트렌드 분석",
    "검색",
    "탐색",
    "실시간 인기",
    "홈",
    "전 세계",
    "지금",
    "에서 무엇을 검색하고 있는지 알아보세요",
    "검색 관심도",
    "지난 24시간",
    "이(가) 인기 있는 이유는 무엇일까요?",
    "상세 데이터 검토",
    "트렌드 데이터팀",
    "선별한 문제와 이벤트",
    "트렌드 활용법",
    "언론사",
    "자선단체",
    "전 세계에서",
    "Google 트렌드를 어떻게 사용하고 있는지",
    "확인해보세요",
    "Google 트렌드란 무엇인가요?",
    "Google 트렌드의 기본사항",
    "데이터에 관해 알아보기",
    "로그인",
    "개인정보처리방침",
    "고급 Google 트렌드",
    "도움말",
    "의견 보내기",
}


def _valid_text(text: str, excluded_texts: Set[str]) -> bool:
    """UI 문구를 제외하고 키워드 후보만 남긴다."""
    if not text or len(text) < 2 or len(text) > 100:
        return False
    if text.startswith("http"):
        return False
    if text in excluded_texts:
        return False
    if any(ex in text for ex in excluded_texts):
        return False
    return True


@asynccontextmanager
async def _trend_page(headless: bool = True, page_timeout_ms: int = 60_000):
    """Playwright 페이지 컨텍스트를 열고 자동 종료."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        try:
            await page.goto(
                TREND_URL, wait_until="networkidle", timeout=page_timeout_ms
            )
        except Exception:
            # 네트워크 idle 실패 시 load 이벤트까지 시도
            await page.goto(TREND_URL, wait_until="load", timeout=page_timeout_ms)
        try:
            yield page
        finally:
            await browser.close()


async def _extract_keywords(page: Page, limit: int, excluded_texts: Set[str]) -> list[str]:
    """페이지 내에서 키워드 텍스트를 추출한다."""
    keywords: list[str] = []
    seen: set[str] = set()

    await page.wait_for_timeout(4_000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1_000)

    # 1) 테이블/대표 클래스 우선
    for selector in ("tbody tr .mZ3RIc", ".mZ3RIc"):
        elements = await page.query_selector_all(selector)
        for elem in elements:
            try:
                text = (await elem.inner_text() or "").strip()
            except Exception:
                continue
            if not _valid_text(text, excluded_texts) or text in seen:
                continue
            seen.add(text)
            keywords.append(text)
            if len(keywords) >= limit:
                return keywords

    # 2) 모든 링크에서 추출
    links = await page.query_selector_all("a")
    for link in links:
        try:
            text = (await link.inner_text() or "").strip()
        except Exception:
            continue
        if not _valid_text(text, excluded_texts) or text in seen:
            continue
        seen.add(text)
        keywords.append(text)
        if len(keywords) >= limit:
            return keywords

    # 3) 일반 텍스트 요소에서 추출
    text_elems = await page.query_selector_all("div, span, p, h1, h2, h3, h4, h5")
    for elem in text_elems:
        try:
            raw = (await elem.inner_text() or "").strip()
        except Exception:
            continue
        if not raw:
            continue
        first_line = raw.split("\n")[0].strip()
        if not _valid_text(first_line, excluded_texts) or first_line in seen:
            continue
        seen.add(first_line)
        keywords.append(first_line)
        if len(keywords) >= limit:
            break

    return keywords[:limit]


class GoogleTrendsService:
    """Google Trends 크롤링 서비스."""

    async def fetch_keywords(
        self,
        *,
        limit: int = 20,
        headless: bool = True,
        excluded_texts: Optional[Set[str]] = None,
        page_timeout_ms: int = 60_000,
    ) -> Sequence[str]:
        """
        구글 트렌드 키워드를 문자열 리스트로 반환한다.
        """
        excluded = excluded_texts or EXCLUDED_TEXTS
        try:
            await _log_async("INFO", "구글 트렌드 크롤링 시작", f"limit={limit}")
            async with _trend_page(headless=headless, page_timeout_ms=page_timeout_ms) as page:
                return await _extract_keywords(page, limit, excluded)
        except Exception as exc:  # pragma: no cover - 네트워크/Playwright 예외
            await _log_async("ERROR", "구글 트렌드 크롤링 실패", str(exc))
            return []
        finally:
            await _log_async("INFO", "구글 트렌드 크롤링 종료", f"limit={limit}")

    async def fetch_google_crawler_response(
        self,
        *,
        limit: int = 20,
        headless: bool = True,
        excluded_texts: Optional[Set[str]] = None,
        page_timeout_ms: int = 60_000,
    ) -> list[GoogleTrendItem]:
        """
        API 규격에 맞는 리스트를 반환한다.
        """
        keywords = await self.fetch_keywords(
            limit=limit,
            headless=headless,
            excluded_texts=excluded_texts,
            page_timeout_ms=page_timeout_ms,
        )
        await _log_async("INFO", "구글 트렌드 응답 빌드 완료", f"count={len(keywords)}")
        return [
            GoogleTrendItem(
                categoryId=1,
                keyword=keyword,
                searchVolume=0,
                snsType="google",
            )
            for keyword in keywords
        ]

    def extract_keywords_from_response(
        self, crawler_response: GoogleCrawlerResponse | dict | None
    ) -> list[str]:
        """Google Crawler 응답에서 keyword만 추출한다."""
        if crawler_response is None:
            return []

        try:
            response = (
                crawler_response
                if isinstance(crawler_response, GoogleCrawlerResponse)
                else GoogleCrawlerResponse.model_validate(crawler_response)
            )
        except ValidationError as exc:
            _log_sync("ERROR", "GoogleCrawlerResponse 파싱 실패", str(exc))
            return []

        keywords: list[str] = []
        seen: set[str] = set()
        for item in response.googleCrawler:
            keyword = (item.keyword or "").strip()
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            keywords.append(keyword)
        return keywords
async def _log_async(level: str, message: str, sub: str = "") -> None:
    try:
        await async_send_log(message=message, level=level, submessage=sub, logged_process="trends")
    except Exception:
        return


def _log_sync(level: str, message: str, sub: str = "") -> None:
    try:
        send_log(message=message, level=level, submessage=sub, logged_process="trends")
    except Exception:
        return
