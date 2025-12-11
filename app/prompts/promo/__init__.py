"""프로모션용 시스템 프롬프트/가이드 로더.

플랫폼별 가이드는 동일 디렉터리의 {platform}.txt에서 로드한다.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

DEFAULT_GUIDE = "플랫폼 일반 규칙: 짧고 명확하게, CTA는 한 번만, 과장되지 않게 작성."
BASE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=16)
def get_platform_guide(platform: str) -> str:
    """플랫폼별 가이드라인 텍스트를 반환 (파일 기반)."""
    path = BASE_DIR / f"{platform}.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            return DEFAULT_GUIDE
    return DEFAULT_GUIDE
