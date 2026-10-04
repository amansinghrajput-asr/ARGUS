"""FAQ and Knowledge base domain business logic and service layer."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError
from ..models.knowledge import validate_article_fields
from ..repositories.knowledge_repo import KnowledgeRepository


class KnowledgeService:
    """Encapsulates business rules and persistence operations for FAQ / Knowledge articles."""

    def __init__(self, knowledge_repo: Optional[KnowledgeRepository] = None) -> None:
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()

    async def create_article(self, article_input: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Validate, verify uniqueness, and persist a new FAQ article."""
        data: Dict[str, Any] = (
            article_input.to_dict()
            if hasattr(article_input, "to_dict")
            else dict(article_input)
            if not hasattr(article_input, "model_dump")
            else article_input.model_dump()
        )

        title = data.get("title", "")
        category = data.get("category", "")
        content = data.get("content", "")
        version = data.get("version", 1)
        tags = data.get("tags", [])
        vector_doc_id = data.get("vector_doc_id")
        is_active = data.get("is_active", True)
        article_id = data.get("article_id")

        # 1. Validation
        try:
            validate_article_fields(title=title, category=category, content=content, version=version)
        except ValueError as e:
            raise ValidationError(str(e))

        clean_title = str(title).strip()
        clean_category = str(category).strip().lower()
        clean_content = str(content).strip()

        # 2. Assign unique ID if not supplied
        if not article_id or not str(article_id).strip():
            article_id = f"faq_{uuid.uuid4().hex[:8]}"
        else:
            article_id = str(article_id).strip()

        # 3. Collision check
        existing = await self.knowledge_repo.get_by_id(article_id)
        if existing is not None:
            raise DuplicateEntityError(f"Article with ID '{article_id}' already exists.")

        # 4. Canonical document
        now_iso = datetime.now(timezone.utc).isoformat()
        article_record: Dict[str, Any] = {
            "article_id": article_id,
            "title": clean_title,
            "category": clean_category,
            "content": clean_content,
            "tags": [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else [],
            "vector_doc_id": str(vector_doc_id).strip() if vector_doc_id else None,
            "is_active": bool(is_active),
            "version": int(version),
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # 5. Persist
        return await self.knowledge_repo.create(article_record)

    async def get_article(self, article_id: str) -> Dict[str, Any]:
        """Retrieve FAQ article by unique article_id."""
        if not article_id or not str(article_id).strip():
            raise ValidationError("Invalid article_id provided.")

        clean_id = str(article_id).strip()
        article = await self.knowledge_repo.get_by_id(clean_id)
        if article is None:
            raise EntityNotFoundError(f"Article with ID '{clean_id}' was not found.")
        return article

    async def list_articles(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List FAQ articles with optional category and status filtering."""
        return await self.knowledge_repo.list_articles(category=category, is_active=is_active, limit=limit)
