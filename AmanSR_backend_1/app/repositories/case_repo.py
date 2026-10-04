"""ComplaintCase repository implementation for MongoDB and isolated in-memory operations."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class CaseRepository:
    """Handles persistence operations for ComplaintCase records."""

    def __init__(self, db: Optional[Any] = None) -> None:
        self.db = db
        # In-memory dictionary store for isolated unit tests / environments without MongoDB
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def _clean_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove MongoDB internal _id field and return deep copy."""
        if not doc:
            return None
        cleaned = deepcopy(doc)
        cleaned.pop("_id", None)
        return cleaned

    async def create(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new complaint case document and return the sanitized record."""
        case_id = case_data["case_id"]
        to_save = deepcopy(case_data)

        if self.db is not None:
            await self.db["cases"].insert_one(to_save)
            return self._clean_doc(to_save)  # type: ignore[return-value]

        # Isolated in-memory fallback
        self._memory_store[case_id] = to_save
        return self._clean_doc(to_save)  # type: ignore[return-value]

    async def get_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complaint case by unique case_id with bounded single-doc query."""
        if not case_id or not isinstance(case_id, str):
            return None

        if self.db is not None:
            doc = await self.db["cases"].find_one({"case_id": case_id})
            return self._clean_doc(doc)

        # In-memory fallback
        doc = self._memory_store.get(case_id)
        return self._clean_doc(doc)

    async def update(self, case_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Partially update an existing complaint case document and return the updated record."""
        if not case_id or not isinstance(case_id, str):
            return None

        to_update = deepcopy(update_data)
        to_update.pop("_id", None)
        to_update.pop("case_id", None)
        to_update["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            result = await self.db["cases"].find_one_and_update(
                {"case_id": case_id},
                {"$set": to_update},
                return_document=True,
            )
            return self._clean_doc(result)

        # In-memory fallback
        if case_id not in self._memory_store:
            return None

        doc = self._memory_store[case_id]
        doc.update(to_update)
        return self._clean_doc(doc)

    async def list_cases(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List cases with optional customer_id and status filters using bounded queries."""
        safe_limit = max(1, min(limit, 100))
        query: Dict[str, Any] = {}
        if customer_id:
            query["customer_id"] = customer_id
        if status:
            query["status"] = status

        if self.db is not None:
            cursor = self.db["cases"].find(query).limit(safe_limit)
            docs = await cursor.to_list(length=safe_limit)
            return [self._clean_doc(d) for d in docs if d is not None]  # type: ignore[misc]

        # In-memory fallback
        results = []
        for doc in self._memory_store.values():
            if customer_id and doc.get("customer_id") != customer_id:
                continue
            if status and doc.get("status") != status:
                continue
            results.append(self._clean_doc(doc))
        return [r for r in results[:safe_limit] if r is not None]  # type: ignore[misc]
