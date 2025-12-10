"""Service for generating promotional content."""

from app.schemas.content import ContentDraft, ContentRequest


class ContentService:
    """Stub service that will leverage LangChain + OpenAI."""

    async def generate(self, payload: ContentRequest) -> ContentDraft:
        """Generate promotional content per platform requirements."""
        raise NotImplementedError("콘텐츠 생성이 아직 구현되지 않았습니다.")
