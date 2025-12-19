"""Naver Blog login + publish service using Playwright."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
import contextvars
from typing import Optional
from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - optional dependency for tests
    async_playwright = None  # type: ignore

from app.logs import async_send_log


DEFAULT_SESSION_FILE = "/tmp/naver_blog_session.json"
LOGIN_URL = "https://nid.naver.com/nidlogin.login"
JOB_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar("naver_blog_job_id", default="")


def _log(message: str, *, level: str = "INFO", submessage: str = "", job_id: str | None = None) -> None:
    try:
        job = job_id if job_id is not None else JOB_ID_CTX.get("")
        # fire-and-forget async; if not awaited, it runs in loop via create_task
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                async_send_log(
                    message=message,
                    level=level,
                    submessage=submessage,
                    logged_process="naver_blog",
                    job_id=job,
                )
            )
        else:
            asyncio.run(
                async_send_log(
                    message=message,
                    level=level,
                    submessage=submessage,
                    logged_process="naver_blog",
                    job_id=job,
                )
            )
    except Exception:
        return


def _ensure_session_path(session_file: str) -> None:
    directory = os.path.dirname(session_file)
    if directory:
        os.makedirs(directory, exist_ok=True)


async def _is_session_valid(browser, session_file: str) -> bool:
    if not os.path.exists(session_file):
        return False

    context = await browser.new_context(storage_state=session_file)
    page = await context.new_page()
    _log("기존 세션 검증 중...")
    await page.goto("https://blog.naver.com", timeout=30000)

    # 로그인 페이지로 리디렉트되지 않으면 유효
    return "nidlogin.login" not in page.url


async def _perform_login(browser, login_id: str, login_pw: str, session_file: str) -> bool:
    context = await browser.new_context()
    page = await context.new_page()

    _log("로그인 페이지 이동")
    await page.goto(LOGIN_URL, timeout=30000)
    _log("아이디/비밀번호 입력")
    await page.fill("#id", login_id)
    await page.fill("#pw", login_pw)
    _log("로그인 버튼 클릭")
    await page.click("button[type=submit]")
    await page.wait_for_url(lambda url: "nidlogin.login" not in url, timeout=10000)
    await _confirm_trusted_device(page)
    _log("로그인 성공, 세션 저장")
    await context.storage_state(path=session_file)
    return True


async def _open_editor(browser, blog_id: str, session_file: str):
    context = await browser.new_context(storage_state=session_file)
    page = await context.new_page()
    _log("글쓰기 페이지 이동")
    await page.goto(f"https://blog.naver.com/{blog_id}?Redirect=Write&", timeout=30000)
    _log(f"현재 페이지 URL: {page.url}")
    await page.wait_for_selector("iframe[name='mainFrame']")
    frame = page.frame(name="mainFrame")
    return frame, page


def _find_editor_frame(frame):
    """메인 프레임 내부에서 실제 에디터 iframe을 찾아 반환한다."""
    queue = list(frame.child_frames)
    while queue:
        fr = queue.pop(0)
        name = (fr.name or "") + (fr.url or "")
        if "canvas" in name or "SmartEditor" in name or "edit" in name:
            _log(f"에디터 iframe 발견: name={fr.name}, url={fr.url}")
            return fr
        queue.extend(fr.child_frames)
    _log("에디터 iframe을 찾지 못해 mainFrame 사용", level="WARN")
    return frame


def _collect_frames(root_frame):
    """루트 프레임 포함 모든 자식 프레임을 리스트로 반환."""
    frames = []
    queue = [root_frame]
    while queue:
        fr = queue.pop(0)
        frames.append(fr)
        queue.extend(fr.child_frames)
    return frames


async def _fill_title(frame, title: str) -> bool:
    frames = _collect_frames(frame)
    selectors = [
        "p.se-text-paragraph span.se-placeholder",
        "p.se_textarea span.se_placeholder",
        "div.se_editArea h3.se_textarea",
        "div.se_editArea div.se_title",
        "div[data-testid='title']",
        "div.write_header input[type='text']",
        "[contenteditable='true'][role='textbox']",
    ]
    for fr in frames:
        for sel in selectors:
            try:
                _log(f"제목 입력 시도: {sel} @frame {fr.name} {fr.url}")
                await fr.wait_for_selector(sel, timeout=2000)
                await fr.click(sel, force=True)
                try:
                    await fr.fill(sel, "")  # 혹시 입력 가능하면 비우기
                except Exception:
                    pass
                await fr.type(sel, title)
                return True
            except Exception:
                continue
    # JS로 직접 입력 시도 (마지막 수단)
    try:
        _log("제목 입력 시도: JS fallback")
        for fr in frames:
            try:
                await fr.evaluate(
                    "(text) => { const el = document.querySelector('[contenteditable=\"true\"],[role=\"textbox\"], input[type=\"text\"]'); if (el) { el.focus(); el.innerText = text; el.textContent = text; if(el.value!==undefined) el.value=text; } }",
                    title,
                )
                return True
            except Exception:
                continue
    except Exception:
        pass
    _log("제목 입력 실패 (모든 셀렉터 시도)", level="WARN")
    return False


async def _fill_content(frame, content: str) -> bool:
    frames = _collect_frames(frame)
    selectors = [
        "div.se-module-text p.se-text-paragraph span.se-placeholder",
        "div.se_component_wrap p.se_textarea span.se_placeholder",
        "div.se_editArea p.se_textarea",
        "div.se_component_wrap [contenteditable='true']",
        "div[data-testid='postEditor'] [contenteditable='true']",
        "div.se_component_wrap p.se_textarea",
        "div.write_form [contenteditable='true']",
        "div.se_component_wrap div[contenteditable='true']",
        "[contenteditable='true'][data-placeholder]",
    ]
    for fr in frames:
        for sel in selectors:
            try:
                _log(f"본문 입력 시도: {sel} @frame {fr.name} {fr.url}")
                await fr.wait_for_selector(sel, timeout=2500)
                await fr.click(sel, force=True)
                try:
                    await fr.fill(sel, "")  # 비우기 시도
                except Exception:
                    pass
                await fr.type(sel, content)
                return True
            except Exception:
                continue
    # JS로 직접 입력 시도 (마지막 수단)
    try:
        _log("본문 입력 시도: JS fallback")
        for fr in frames:
            try:
                await fr.evaluate(
                    "(text) => { const el = document.querySelector('[contenteditable=\"true\"]'); if (el) { el.focus(); el.innerText = text; el.textContent = text; } }",
                    content,
                )
                return True
            except Exception:
                continue
    except Exception:
        pass
    _log("본문 입력 실패 (모든 셀렉터 시도)", level="WARN")
    return False


async def _publish(frame) -> bool:
    frames = _collect_frames(frame)
    selectors = [
        "button.publish_btn__m9KHH",
        "button[data-testid='seOnePublishBtn']",
        "button:has-text('발행')",
    ]
    clicked = False
    for fr in frames:
        for sel in selectors:
            try:
                _log(f"발행 버튼 클릭 시도: {sel} @frame {fr.name} {fr.url}")
                await fr.wait_for_selector(sel, timeout=2500)
                await fr.click(sel, force=True)
                clicked = True
            except Exception:
                continue
    return clicked


async def _close_existing_draft(frame) -> None:
    """작성 중이던 글 팝업이 있으면 닫는다."""
    selectors = [
        "button.se-popup-button-cancel",
        "button.se-popup-button-close",
        "button[class*='popup']",
    ]
    for sel in selectors:
        try:
            await frame.wait_for_selector(sel, timeout=2000)
            await frame.click(sel, force=True)
            _log(f"기존 작성 팝업 닫음: {sel}")
            return
        except Exception:
            continue


async def _confirm_trusted_device(page) -> None:
    """자주 사용하는 기기 등록 안내가 뜨면 등록/확인을 눌러 통과."""
    selectors = [
        "button[type='submit'][id*='trust']",
        "button:has-text('등록')",
        "button:has-text('확인')",
        "button:has-text('Continue')",
        "button:has-text('Verify')",
        "button:has-text('다음')",
    ]
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=2000)
            await page.click(sel, force=True)
            _log(f"자주 사용하는 기기 등록/확인 처리: {sel}")
            await asyncio.sleep(0.5)
            return
        except Exception:
            continue


async def _close_help_panel(frame) -> None:
    """도움말/가이드 패널 닫기."""
    selectors = [
        "button.se-help-panel-close-button",
        "button[aria-label*='닫기']",
        "button:has-text('닫기')",
    ]
    for sel in selectors:
        try:
            await frame.wait_for_selector(sel, timeout=2000)
            await frame.click(sel, force=True)
            _log(f"도움말 패널 닫음: {sel}")
            return
        except Exception:
            continue


@dataclass
class NaverBlogPublishResult:
    success: bool
    message: str
    url: Optional[str] = None


class NaverBlogService:
    """네이버 블로그 로그인 + 게시글 업로드 서비스."""

    async def publish(
        self,
        *,
        login_id: str,
        login_pw: str,
        title: str,
        content: str,
        blog_id: Optional[str] = None,
        session_file: str = DEFAULT_SESSION_FILE,
        headless: bool = False,
        job_id: Optional[str] = None,
    ) -> NaverBlogPublishResult:
        if async_playwright is None:
            raise ImportError("playwright 패키지가 필요합니다.")
        blog_target = blog_id or login_id
        _ensure_session_path(session_file)
        token = JOB_ID_CTX.set(job_id or "")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)

            try:
                # 세션 유효성 검사 후 필요 시 로그인
                _log("로그인/세션 확인 시작")
                valid = await _is_session_valid(browser, session_file)
                if not valid:
                    _log("세션 없음/만료 → 로그인 수행")
                    logged_in = await _perform_login(browser, login_id, login_pw, session_file)
                    if not logged_in:
                        return NaverBlogPublishResult(False, "로그인 실패")
                else:
                    _log("기존 세션 사용")

                frame, page = await _open_editor(browser, blog_target, session_file)
                await _confirm_trusted_device(page)
                await _close_existing_draft(frame)
                await _close_help_panel(frame)

                if not await _fill_title(frame, title):
                    return NaverBlogPublishResult(False, "제목 입력 실패")

                if not await _fill_content(frame, content):
                    return NaverBlogPublishResult(False, "본문 입력 실패")

                if not await _publish(frame):
                    return NaverBlogPublishResult(False, "발행 버튼 클릭 실패")

                # 발행 후 URL을 베스트에포트로 획득
                _log("발행 완료, URL 확인 중")
                await asyncio.sleep(1.5)
                final_url = page.url
                if "PostView.naver" not in final_url:
                    # try to wait a bit more
                    try:
                        await page.wait_for_url(lambda url: "PostView.naver" in url, timeout=5000)
                        final_url = page.url
                    except Exception:
                        pass
                return NaverBlogPublishResult(True, "게시물 발행 완료", final_url)

            except Exception as exc:
                _log("오류 발생", level="ERROR", submessage=str(exc))
                return NaverBlogPublishResult(False, f"오류 발생: {exc}")
            finally:
                JOB_ID_CTX.reset(token)
                await browser.close()
