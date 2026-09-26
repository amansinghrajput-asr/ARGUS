"""FAQ / Knowledge repository placeholder for MongoDB operations."""

from typing import Any, List, Optional


class KnowledgeRepository:
    """Handles persistence operations for FAQ / Knowledge base articles."""

    def __init__(self, db: Optional[Any] = None) -> None:
        self.db = db

    async def get_by_id(self, article_id: str) -> Optional[dict]:
        """Fetch article by ID (placeholder)."""
        if self.db is None:
            return None
        return await self.db["faq_articles"].find_one({"article_id": article_id})

    async def list_by_category(self, category: Optional[str] = None, limit: int = 10) -> List[dict]:
        """List active FAQ articles by category (placeholder)."""
        if self.db is None:
            return []
        query: dict = {"is_active": True}
        if category:
            query["category"] = category
        cursor = self.db["faq_articles"].find(query).limit(limit)
        return await cursor.to_list(length=limit)
