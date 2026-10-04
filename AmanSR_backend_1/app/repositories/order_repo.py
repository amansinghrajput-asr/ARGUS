"""Order repository implementation for MongoDB and isolated in-memory operations."""

from copy import deepcopy
from typing import Any, Dict, List, Optional


class OrderRepository:
    """Handles persistence operations for Order records."""

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

    async def create(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new order document and return the sanitized record."""
        order_id = order_data["order_id"]
        to_save = deepcopy(order_data)

        if self.db is not None:
            await self.db["orders"].insert_one(to_save)
            return self._clean_doc(to_save)  # type: ignore[return-value]

        # Isolated in-memory fallback
        self._memory_store[order_id] = to_save
        return self._clean_doc(to_save)  # type: ignore[return-value]

    async def get_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch order record by unique order_id with bounded single-doc query."""
        if not order_id or not isinstance(order_id, str):
            return None

        if self.db is not None:
            doc = await self.db["orders"].find_one({"order_id": order_id})
            return self._clean_doc(doc)

        # In-memory fallback
        doc = self._memory_store.get(order_id)
        return self._clean_doc(doc)

    async def get_by_customer_id(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch all orders belonging to a customer using a bounded query."""
        if not customer_id or not isinstance(customer_id, str):
            return []

        safe_limit = max(1, min(limit, 100))

        if self.db is not None:
            cursor = self.db["orders"].find({"customer_id": customer_id}).limit(safe_limit)
            docs = await cursor.to_list(length=safe_limit)
            return [self._clean_doc(d) for d in docs if d is not None]  # type: ignore[misc]

        # In-memory fallback
        matched = [d for d in self._memory_store.values() if d.get("customer_id") == customer_id]
        return [self._clean_doc(d) for d in matched[:safe_limit] if d is not None]  # type: ignore[misc]

    async def list_by_customer_id(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Backward-compatible alias for fetching orders by customer_id."""
        return await self.get_by_customer_id(customer_id, limit=limit)

    async def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Bounded listing of orders (for internal/testing use)."""
        safe_limit = max(1, min(limit, 100))
        if self.db is not None:
            cursor = self.db["orders"].find({}).limit(safe_limit)
            docs = await cursor.to_list(length=safe_limit)
            return [self._clean_doc(d) for d in docs if d is not None]  # type: ignore[misc]

        # In-memory fallback
        return [self._clean_doc(d) for d in list(self._memory_store.values())[:safe_limit] if d is not None]  # type: ignore[misc]
