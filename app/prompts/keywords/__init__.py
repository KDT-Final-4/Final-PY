"""쇼핑몰 검색어 생성 프롬프트 로더."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSTEM = (
    "너는 이커머스 검색어 기획자다. 입력된 트렌드 키워드를 보고 실제 쇼핑몰 검색에 쓸 만한 "
    "키워드(real_keyword)를 제안하고, 그 이유를 간단히 설명한다.\n"
    "- keyword는 입력 그대로 보존\n"
    "- real_keyword는 keyword를 그대로 쓰거나, 사람이 자주 쓰는 형태로 자연스럽게 변형\n"
    "- reason은 선택 근거를 한두 문장으로 작성\n"
    "- 출력은 JSON(keyword, real_keyword, reason)만 반환"
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
