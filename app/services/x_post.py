"""X(Twitter) OAuth1 게시 서비스 (tweepy 사용)."""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import tweepy

from app import config
from app.logs import async_send_log


def _build_status(title: str, content: str, limit: int = 280) -> str:
    """제목 + 본문을 합쳐 280자 내로 자르고 깔끔하게 만든다."""
    text = f"{title}\n\n{content}".strip()
    text = re.sub(r"\s+", " ", text)  # 줄바꿈/중복 공백 축약
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


class XPostService:
    """X(Twitter) 게시 서비스 (OAuth1 → tweepy.Client v2 /2/tweets)."""

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
    ):
        # None으로 두고, 실제 호출 시 요청값 → 환경변수 순으로 폴백한다.
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

    def post(
        self,
        title: str,
        content: str,
        *,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
    ) -> str:
        """트윗을 게시하고 URL을 반환한다 (v2 create_tweet)."""
        status = _build_status(title, content)

        ck = consumer_key or self.consumer_key or config.get_x_consumer_key()
        cs = consumer_secret or self.consumer_secret or config.get_x_consumer_secret()
        at = access_token or self.access_token or config.get_x_access_token()
        ats = access_token_secret or self.access_token_secret or config.get_x_access_token_secret()

        # tweepy Client with OAuth1 user context
        client = tweepy.Client(
            consumer_key=ck,
            consumer_secret=cs,
            access_token=at,
            access_token_secret=ats,
            wait_on_rate_limit=True,
        )

        # INFO 로그
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    async_send_log(
                        message="X 업로드 시작",
                        submessage=f"title_preview={status[:40]}",
                        logged_process="x_post",
                    )
                )
        except Exception:
            pass

        resp = client.create_tweet(text=status)
        # resp can be Tweepy Response or dict
        if hasattr(resp, "data"):
            data = resp.data or {}
        elif isinstance(resp, dict):
            data = resp.get("data", {}) or {}
        else:
            data = {}

        tweet_id = data.get("id")
        if not tweet_id:
            raise RuntimeError(f"트윗 ID를 찾지 못했습니다: {resp}")
        url = f"https://twitter.com/i/web/status/{tweet_id}"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    async_send_log(
                        message="X 업로드 완료",
                        submessage=f"url={url}",
                        logged_process="x_post",
                    )
                )
        except Exception:
            pass
        return url

    async def post_async(
        self,
        title: str,
        content: str,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(self.post, title, content, **kwargs)
