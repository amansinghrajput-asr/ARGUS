"""ConversationHistory repository implementation for MongoDB and isolated in-memory operations."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class HistoryRepository:
    """Handles persistence operations for ConversationHistory records."""

    def __init__(self, db: Optional[Any] = None) -> None:
        self.db = db
        # In-memory dictionary store keyed by case_id for isolated unit tests / environments without MongoDB
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def _clean_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove MongoDB internal _id field and return deep copy."""
        if not doc:
            return None
        cleaned = deepcopy(doc)
        cleaned.pop("_id", None)
        return cleaned

    async def get_by_case_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch conversation history document by unique case_id."""
        if not case_id or not isinstance(case_id, str):
            return None

        clean_id = case_id.strip()
        if self.db is not None:
            doc = await self.db["conversation_histories"].find_one({"case_id": clean_id})
            return self._clean_doc(doc)

        # In-memory fallback
        doc = self._memory_store.get(clean_id)
        return self._clean_doc(doc)

    async def create_history(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize and persist a new conversation history record for a case."""
        case_id = str(history_data["case_id"]).strip()
        to_save = deepcopy(history_data)

        if self.db is not None:
            await self.db["conversation_histories"].insert_one(to_save)
            return self._clean_doc(to_save)  # type: ignore[return-value]

        # Isolated in-memory fallback
        self._memory_store[case_id] = to_save
        return self._clean_doc(to_save)  # type: ignore[return-value]

    async def append_conversation_turn(self, case_id: str, turn_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Append a message turn to the case conversation history and return updated record."""
        if not case_id or not isinstance(case_id, str):
            return None

        clean_id = case_id.strip()
        clean_turn = deepcopy(turn_data)
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            updated = await self.db["conversation_histories"].find_one_and_update(
                {"case_id": clean_id},
                {
                    "$push": {"messages": clean_turn},
                    "$set": {"updated_at": now_iso},
                },
                return_document=True,
            )
            return self._clean_doc(updated)

        # In-memory fallback
        doc = self._memory_store.get(clean_id)
        if doc is None:
            return None
        doc.setdefault("messages", []).append(clean_turn)
        doc["updated_at"] = now_iso
        return self._clean_doc(doc)

    async def append_message_turn(self, case_id: str, turn_data: dict) -> bool:
        """Backward-compatible alias for appending a message turn."""
        res = await self.append_conversation_turn(case_id, turn_data)
        return res is not None

    async def append_investigation_note(self, case_id: str, note_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Append a specialist note to the investigation trail and return updated record."""
        if not case_id or not isinstance(case_id, str):
            return None

        clean_id = case_id.strip()
        clean_note = deepcopy(note_data)
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            updated = await self.db["conversation_histories"].find_one_and_update(
                {"case_id": clean_id},
                {
                    "$push": {"investigation_trail": clean_note},
                    "$set": {"updated_at": now_iso},
                },
                return_document=True,
            )
            return self._clean_doc(updated)

        # In-memory fallback
        doc = self._memory_store.get(clean_id)
        if doc is None:
            return None
        doc.setdefault("investigation_trail", []).append(clean_note)
        doc["updated_at"] = now_iso
        return self._clean_doc(doc)

    async def update_handoff_summary(self, case_id: str, summary: str) -> Optional[Dict[str, Any]]:
        """Update the compiled human handoff summary in the conversation history record."""
        if not case_id or not isinstance(case_id, str):
            return None

        clean_id = case_id.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            updated = await self.db["conversation_histories"].find_one_and_update(
                {"case_id": clean_id},
                {"$set": {"human_handoff_summary": summary, "updated_at": now_iso}},
                return_document=True,
            )
            return self._clean_doc(updated)

        # In-memory fallback
        doc = self._memory_store.get(clean_id)
        if doc is None:
            return None
        doc["human_handoff_summary"] = summary
        doc["updated_at"] = now_iso
        return self._clean_doc(doc)

    async def get_handoff_info(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation history and notes for handoff packet compilation."""
        return await self.get_by_case_id(case_id)
