"""Knowledge base and FAQ article model schema placeholder."""

from typing import List, Optional
from datetime import datetime

try:
    from pydantic import BaseModel, Field

    class FAQArticleBase(BaseModel):
        """Minimal schema for FAQ / Knowledge base article."""

        article_id: str
        title: str
        category: str  # billing, refunds, shipping, technical, account
        content: str
        tags: List[str] = Field(default_factory=list)
        vector_doc_id: Optional[str] = None  # Reference pointer to vector store chunk
        is_active: bool = True
        version: int = 1
        updated_at: Optional[datetime] = None

except ImportError:
    class FAQArticleBase:  # type: ignore[no-redef]
        def __init__(
            self,
            article_id: str,
            title: str,
            category: str,
            content: str,
            tags: Optional[List[str]] = None,
            vector_doc_id: Optional[str] = None,
        ) -> None:
            self.article_id = article_id
            self.title = title
            self.category = category
            self.content = content
            self.tags = tags or []
            self.vector_doc_id = vector_doc_id
            self.is_active = True
            self.version = 1
