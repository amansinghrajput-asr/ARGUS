"""Knowledge base and FAQ article domain models and request/response schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

VALID_CATEGORIES = {"billing", "refunds", "shipping", "technical", "account", "general"}


def validate_article_fields(
    title: str,
    category: str,
    content: str,
    version: int = 1,
) -> None:
    """Validate core FAQ article fields."""
    if not title or not str(title).strip():
        raise ValueError("Article 'title' must not be empty.")
    if not category or not str(category).strip():
        raise ValueError("Article 'category' must not be empty.")
    if not content or not str(content).strip():
        raise ValueError("Article 'content' must not be empty.")
    if not isinstance(version, int) or version < 1:
        raise ValueError("Article 'version' must be an integer >= 1.")


try:
    from pydantic import BaseModel, Field, field_validator

    class ArticleCreate(BaseModel):
        """Schema for FAQ article creation request."""

        title: str = Field(..., min_length=1, description="Article title")
        category: str = Field(..., min_length=1, description="Article topic category")
        content: str = Field(..., min_length=1, description="Detailed resolution or policy content")
        article_id: Optional[str] = Field(default=None, description="Optional custom unique article ID")
        tags: List[str] = Field(default_factory=list, description="Keywords and tags for lookup")
        vector_doc_id: Optional[str] = Field(default=None, description="Canonical pointer to vector store chunk")
        is_active: bool = Field(default=True, description="Whether article is published and active")
        version: int = Field(default=1, ge=1, description="Article revision version number")

        @field_validator("title")
        @classmethod
        def validate_title(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Article 'title' must not be empty.")
            return v.strip()

        @field_validator("category")
        @classmethod
        def validate_category(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Article 'category' must not be empty.")
            return v.strip().lower()

        @field_validator("content")
        @classmethod
        def validate_content(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Article 'content' must not be empty.")
            return v.strip()

    class ArticleResponse(BaseModel):
        """Clean API response model for FAQArticle entity."""

        article_id: str
        title: str
        category: str
        content: str
        tags: List[str] = Field(default_factory=list)
        vector_doc_id: Optional[str] = None
        is_active: bool = True
        version: int = 1
        created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class FAQArticleBase(ArticleResponse):
        """Base FAQ article model representation for scaffolding compatibility."""
        pass

    FAQArticleCreate = ArticleCreate
    FAQArticleResponse = ArticleResponse

except ImportError:
    class ArticleCreate:  # type: ignore[no-redef]
        """Fallback schema for article creation request."""

        def __init__(
            self,
            title: str,
            category: str,
            content: str,
            article_id: Optional[str] = None,
            tags: Optional[List[str]] = None,
            vector_doc_id: Optional[str] = None,
            is_active: bool = True,
            version: int = 1,
        ) -> None:
            validate_article_fields(title=title, category=category, content=content, version=version)
            self.title = str(title).strip()
            self.category = str(category).strip().lower()
            self.content = str(content).strip()
            self.article_id = str(article_id).strip() if article_id else None
            self.tags = list(tags) if tags else []
            self.vector_doc_id = str(vector_doc_id).strip() if vector_doc_id else None
            self.is_active = bool(is_active)
            self.version = int(version)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "article_id": self.article_id,
                "title": self.title,
                "category": self.category,
                "content": self.content,
                "tags": self.tags,
                "vector_doc_id": self.vector_doc_id,
                "is_active": self.is_active,
                "version": self.version,
            }

    class ArticleResponse:  # type: ignore[no-redef]
        """Fallback schema for article response."""

        def __init__(
            self,
            article_id: str,
            title: str,
            category: str,
            content: str,
            tags: Optional[List[str]] = None,
            vector_doc_id: Optional[str] = None,
            is_active: bool = True,
            version: int = 1,
            created_at: Optional[str] = None,
            updated_at: Optional[str] = None,
        ) -> None:
            self.article_id = article_id
            self.title = title
            self.category = category
            self.content = content
            self.tags = list(tags) if tags else []
            self.vector_doc_id = vector_doc_id
            self.is_active = is_active
            self.version = version
            now_iso = datetime.now(timezone.utc).isoformat()
            self.created_at = created_at or now_iso
            self.updated_at = updated_at or now_iso

        def to_dict(self) -> Dict[str, Any]:
            return {
                "article_id": self.article_id,
                "title": self.title,
                "category": self.category,
                "content": self.content,
                "tags": self.tags,
                "vector_doc_id": self.vector_doc_id,
                "is_active": self.is_active,
                "version": self.version,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    class FAQArticleBase(ArticleResponse):  # type: ignore[no-redef]
        pass

    FAQArticleCreate = ArticleCreate  # type: ignore[assignment,misc]
    FAQArticleResponse = ArticleResponse  # type: ignore[assignment,misc]
