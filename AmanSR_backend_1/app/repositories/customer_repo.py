"""Customer repository implementation for MongoDB and isolated in-memory operations."""

from copy import deepcopy
from typing import Any, Dict, List, Optional


class CustomerRepository:
    """Handles persistence operations for Customer records."""

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

    async def create(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new customer document and return the sanitized record."""
        customer_id = customer_data["customer_id"]
        to_save = deepcopy(customer_data)

        if self.db is not None:
            await self.db["customers"].insert_one(to_save)
            return self._clean_doc(to_save)  # type: ignore[return-value]

        # Isolated in-memory fallback
        self._memory_store[customer_id] = to_save
        return self._clean_doc(to_save)  # type: ignore[return-value]

    async def get_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer record by unique customer_id with bounded single-doc query."""
        if not customer_id or not isinstance(customer_id, str):
            return None

        if self.db is not None:
            doc = await self.db["customers"].find_one({"customer_id": customer_id})
            return self._clean_doc(doc)

        # In-memory fallback
        doc = self._memory_store.get(customer_id)
        return self._clean_doc(doc)

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Bounded single-document lookup by exact normalized email."""
        if not email or not isinstance(email, str):
            return None

        clean_email = email.strip().lower()
        if self.db is not None:
            doc = await self.db["customers"].find_one({"email": clean_email})
            return self._clean_doc(doc)

        # In-memory fallback
        for doc in self._memory_store.values():
            if doc.get("email", "").lower() == clean_email:
                return self._clean_doc(doc)
        return None

    async def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Bounded single-document lookup by exact phone string."""
        if not phone or not isinstance(phone, str):
            return None

        clean_phone = phone.strip()
        if self.db is not None:
            doc = await self.db["customers"].find_one({"phone": clean_phone})
            return self._clean_doc(doc)

        # In-memory fallback
        for doc in self._memory_store.values():
            if doc.get("phone") == clean_phone:
                return self._clean_doc(doc)
        return None

    async def lookup(self, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Lookup customer by either email or phone with priority to email."""
        if email:
            customer = await self.find_by_email(email)
            if customer:
                return customer
        if phone:
            return await self.find_by_phone(phone)
        return None

    async def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Bounded listing of customers (for internal/testing use)."""
        safe_limit = max(1, min(limit, 100))
        if self.db is not None:
            cursor = self.db["customers"].find({}).limit(safe_limit)
            docs = await cursor.to_list(length=safe_limit)
            return [self._clean_doc(d) for d in docs if d is not None]  # type: ignore[misc]

        # In-memory fallback
        return [self._clean_doc(d) for d in list(self._memory_store.values())[:safe_limit] if d is not None]  # type: ignore[misc]
