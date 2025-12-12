"""연관도 평가용 프롬프트 로더.

시스템/플랫폼 가이드라인은 동일 디렉터리의 txt 파일에서 로드한다.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSTEM = (
    "너는 상품 추천 평가자다. 키워드와 상품 설명을 보고 연관도를 0.0~1.0 사이 점수로 매겨라.\n"
    "- 1.0에 가까울수록 키워드와 상품이 매우 잘 맞는다.\n"
    "- 출력은 JSON으로 score(0.0~1.0), reason(간단한 근거)만 포함한다.\n"
    "- JSON 외의 추가 텍스트는 넣지 않는다."
)


@lru_cache(maxsize=4)
def get_system_prompt() -> str:
    path = BASE_DIR / "system.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            return DEFAULT_SYSTEM
    return DEFAULT_SYSTEM
