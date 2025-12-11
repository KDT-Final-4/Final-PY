"""Schemas for generated content."""

from pydantic import BaseModel, Field

from app.schemas.products import ProductDetail


class ContentRequest(BaseModel):
    """Input for generating promotional content."""

    title: str = Field(..., description="게시글 제목")
    body: str = Field(..., description="원본 본문 또는 요약")
    ssadagu_product: ProductDetail | None = Field(None, description="싸다구 상품 정보")
    platform: str = Field(..., description="생성 대상 플랫폼 (예: naver_blog, x)")


class ContentDraft(BaseModel):
    """Generated content ready for publishing."""

    platform: str = Field(..., description="대상 플랫폼")
    content: str = Field(..., description="플랫폼 규칙에 맞게 생성된 본문")


class NaverBlogPublishRequest(BaseModel):
    """네이버 블로그 업로드 요청."""

    login_id: str = Field(..., description="네이버 로그인 아이디")
    login_pw: str = Field(..., description="네이버 로그인 비밀번호")
    title: str = Field(..., description="블로그 글 제목")
    content: str = Field(..., description="블로그 글 내용(텍스트)")
    blog_id: str | None = Field(
        None,
        description="블로그 ID (없으면 login_id 사용)",
    )


class NaverBlogPublishResponse(BaseModel):
    """네이버 블로그 업로드 결과."""

    success: bool = Field(..., description="업로드 성공 여부")
    message: str = Field(..., description="결과 메시지")
    url: str | None = Field(None, description="발행된 글 URL(성공 시)")
