"""Service for publishing content to various platforms."""

from app.schemas.publish import PublishRequest, PublishResult


class PublisherService:
    """Stub publisher; concrete platform clients will be added later."""

    async def publish(self, payload: PublishRequest) -> PublishResult:
        """Publish content to the requested platform."""
        raise NotImplementedError("업로드 기능이 아직 구현되지 않았습니다.")
