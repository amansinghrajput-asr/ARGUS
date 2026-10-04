"""FAQ / Knowledge repository implementation for MongoDB and isolated in-memory operations."""

from copy import deepcopy
from typing import Any, Dict, List, Optional


class KnowledgeRepository:
    """Handles persistence operations for FAQ / Knowledge base articles."""

    def __init__(self, db: Optional[Any] = None) -> None:
        self.db = db
        # In-memory dictionary store keyed by article_id for isolated unit tests / environments without MongoDB
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def _clean_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove MongoDB internal _id field and return deep copy."""
        if not doc:
            return None
        cleaned = deepcopy(doc)
        cleaned.pop("_id", None)
        return cleaned

    async def create(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new FAQ article document and return the sanitized record."""
        article_id = str(article_data["article_id"]).strip()
        to_save = deepcopy(article_data)

        if self.db is not None:
            await self.db["faq_articles"].insert_one(to_save)
            return self._clean_doc(to_save)  # type: ignore[return-value]

        # Isolated in-memory fallback
        self._memory_store[article_id] = to_save
        return self._clean_doc(to_save)  # type: ignore[return-value]

    async def get_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch article by unique article_id with bounded single-doc query."""
        if not article_id or not isinstance(article_id, str):
            return None

        clean_id = article_id.strip()
        if self.db is not None:
            doc = await self.db["faq_articles"].find_one({"article_id": clean_id})
            return self._clean_doc(doc)

        # In-memory fallback
        doc = self._memory_store.get(clean_id)
        return self._clean_doc(doc)

    async def list_articles(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List FAQ articles with optional category and active filters using bounded queries."""
        safe_limit = max(1, min(limit, 100))
        query: Dict[str, Any] = {}
        if category:
            query["category"] = category.strip().lower()
        if is_active is not None:
            query["is_active"] = is_active

        if self.db is not None:
            cursor = self.db["faq_articles"].find(query).limit(safe_limit)
            docs = await cursor.to_list(length=safe_limit)
            return [self._clean_doc(d) for d in docs if d is not None]  # type: ignore[misc]

        # In-memory fallback
        results = []
        clean_cat = category.strip().lower() if category else None
        for doc in self._memory_store.values():
            if clean_cat and doc.get("category", "").lower() != clean_cat:
                continue
            if is_active is not None and doc.get("is_active") != is_active:
                continue
            results.append(self._clean_doc(doc))
        return [r for r in results[:safe_limit] if r is not None]  # type: ignore[misc]

    async def list_by_category(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Backward-compatible alias for listing active FAQ articles by category."""
        return await self.list_articles(category=category, is_active=True, limit=limit)
