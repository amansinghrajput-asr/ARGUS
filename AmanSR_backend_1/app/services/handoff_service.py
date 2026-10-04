"""Zero-repeat human handoff packet compiler and conversation history service."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import EntityNotFoundError, ValidationError
from ..models.history import validate_note_fields, validate_turn_fields
from ..repositories.case_repo import CaseRepository
from ..repositories.customer_repo import CustomerRepository
from ..repositories.history_repo import HistoryRepository
from ..repositories.order_repo import OrderRepository


class HandoffService:
    """Manages conversation turns, specialist investigation notes, and compiles zero-repeat handoffs."""

    def __init__(
        self,
        history_repo: Optional[HistoryRepository] = None,
        case_repo: Optional[CaseRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
        order_repo: Optional[OrderRepository] = None,
    ) -> None:
        self.history_repo = history_repo or HistoryRepository()
        self.case_repo = case_repo
        self.customer_repo = customer_repo
        self.order_repo = order_repo

    async def get_or_create_history(self, case_id: str) -> Dict[str, Any]:
        """Fetch existing conversation history or initialize a new record for a valid case."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        clean_id = str(case_id).strip()
        customer_id = "unknown_customer"

        # Verify referenced case exists if case repository is attached
        if self.case_repo is not None:
            case = await self.case_repo.get_by_id(clean_id)
            if case is None:
                raise EntityNotFoundError(f"Case with ID '{clean_id}' was not found.")
            customer_id = case.get("customer_id", "unknown_customer")

        history = await self.history_repo.get_by_case_id(clean_id)
        if history is not None:
            return history

        # Initialize history record for case
        now_iso = datetime.now(timezone.utc).isoformat()
        new_record: Dict[str, Any] = {
            "history_id": f"hist_{uuid.uuid4().hex[:10]}",
            "case_id": clean_id,
            "customer_id": customer_id,
            "messages": [],
            "investigation_trail": [],
            "human_handoff_summary": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        return await self.history_repo.create_history(new_record)

    async def get_history(self, case_id: str) -> Dict[str, Any]:
        """Retrieve conversation history for a given case."""
        return await self.get_or_create_history(case_id)

    async def add_turn(
        self,
        case_id: str,
        turn_input: Union[Dict[str, Any], Any],
    ) -> Dict[str, Any]:
        """Validate and append a conversation message turn."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        data: Dict[str, Any] = (
            turn_input.to_dict()
            if hasattr(turn_input, "to_dict")
            else dict(turn_input)
            if not hasattr(turn_input, "model_dump")
            else turn_input.model_dump()
        )

        sender = data.get("sender") or data.get("role") or data.get("speaker") or ""
        message_text = data.get("message_text") or data.get("message") or data.get("content") or ""
        timestamp = data.get("timestamp")
        detected_intent = data.get("detected_intent")

        try:
            validate_turn_fields(sender=str(sender), message_text=str(message_text))
        except ValueError as e:
            raise ValidationError(str(e))

        clean_id = str(case_id).strip()
        history = await self.get_or_create_history(clean_id)
        existing_turns = history.get("messages", [])
        turn_id = len(existing_turns) + 1

        turn_record: Dict[str, Any] = {
            "turn_id": turn_id,
            "sender": str(sender).strip(),
            "message_text": str(message_text).strip(),
            "timestamp": str(timestamp).strip() if timestamp else datetime.now(timezone.utc).isoformat(),
            "detected_intent": str(detected_intent).strip() if detected_intent else None,
        }

        updated = await self.history_repo.append_conversation_turn(clean_id, turn_record)
        if updated is None:
            raise EntityNotFoundError(f"Case history for '{clean_id}' could not be updated.")
        return updated

    async def add_note(
        self,
        case_id: str,
        note_input: Union[Dict[str, Any], Any],
    ) -> Dict[str, Any]:
        """Validate and append an investigation trail note."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        data: Dict[str, Any] = (
            note_input.to_dict()
            if hasattr(note_input, "to_dict")
            else dict(note_input)
            if not hasattr(note_input, "model_dump")
            else note_input.model_dump()
        )

        specialist = data.get("specialist") or data.get("agent") or ""
        action_taken = data.get("action_taken") or data.get("note") or ""
        result = data.get("result") or data.get("details") or ""
        timestamp = data.get("timestamp")

        try:
            validate_note_fields(
                specialist=str(specialist),
                action_taken=str(action_taken),
                result=str(result),
            )
        except ValueError as e:
            raise ValidationError(str(e))

        clean_id = str(case_id).strip()
        await self.get_or_create_history(clean_id)

        note_record: Dict[str, Any] = {
            "specialist": str(specialist).strip(),
            "action_taken": str(action_taken).strip(),
            "result": str(result).strip(),
            "timestamp": str(timestamp).strip() if timestamp else datetime.now(timezone.utc).isoformat(),
        }

        updated = await self.history_repo.append_investigation_note(clean_id, note_record)
        if updated is None:
            raise EntityNotFoundError(f"Investigation trail for '{clean_id}' could not be updated.")
        return updated

    async def compile_handoff_packet(self, case_id: str) -> Dict[str, Any]:
        """Assemble customer context, turns, specialist findings, and structured summary for zero-repeat handoff."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        clean_id = str(case_id).strip()

        # 1. Fetch case details
        case: Dict[str, Any] = {}
        if self.case_repo is not None:
            found_case = await self.case_repo.get_by_id(clean_id)
            if found_case is None:
                raise EntityNotFoundError(f"Case with ID '{clean_id}' was not found.")
            case = found_case

        customer_id = case.get("customer_id", "unknown_customer")
        customer_name: Optional[str] = None
        customer_email: Optional[str] = None

        # 2. Fetch customer details if available
        if customer_id and customer_id != "unknown_customer" and self.customer_repo is not None:
            cust = await self.customer_repo.get_by_id(customer_id)
            if cust:
                customer_name = cust.get("name")
                customer_email = cust.get("email")

        # 3. Fetch conversation history and investigation trail
        history = await self.history_repo.get_by_case_id(clean_id)
        messages: List[Dict[str, Any]] = history.get("messages", []) if history else []
        trail: List[Dict[str, Any]] = history.get("investigation_trail", []) if history else []

        # 4. Generate structured zero-repeat summary
        complaint_text = case.get("raw_complaint") or case.get("raw_complaint_text") or "Complaint details pending."
        case_num = case.get("case_number", clean_id)
        status_val = case.get("status", "open")
        priority_val = case.get("priority", "medium")
        category_val = case.get("category", "general")
        order_ref = case.get("order_id")

        summary_parts = [
            f"Case {case_num} ({priority_val.upper()} / {category_val}) — Status: {status_val.upper()}.",
            f"Customer: {customer_name or customer_id} ({customer_email or 'No email provided'}).",
            f"Raw Complaint: {complaint_text}",
        ]
        if order_ref:
            summary_parts.append(f"Referenced Order: {order_ref}.")

        if messages:
            summary_parts.append(f"Conversation Turns Logged: {len(messages)} turns.")
        else:
            summary_parts.append("Conversation Turns Logged: None recorded.")

        if trail:
            actions_summary = "; ".join(f"[{n.get('specialist')}]: {n.get('action_taken')} -> {n.get('result')}" for n in trail)
            summary_parts.append(f"Specialist Findings: {actions_summary}")
        else:
            summary_parts.append("Specialist Findings: No investigation actions recorded yet.")

        if case.get("escalation_reason"):
            summary_parts.append(f"Escalation Reason: {case.get('escalation_reason')}")
        if case.get("resolution_summary"):
            summary_parts.append(f"Resolution Details: {case.get('resolution_summary')}")

        handoff_summary = " \n".join(summary_parts)

        # Update persisted handoff summary
        await self.history_repo.update_handoff_summary(clean_id, handoff_summary)

        return {
            "case_id": clean_id,
            "case_number": case.get("case_number"),
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "raw_complaint": complaint_text,
            "category": category_val,
            "priority": priority_val,
            "status": status_val,
            "order_id": order_ref,
            "confidence_score": case.get("confidence_score"),
            "resolution_summary": case.get("resolution_summary"),
            "escalation_reason": case.get("escalation_reason"),
            "assigned_agent": case.get("assigned_agent"),
            "conversation_turns": messages,
            "investigation_trail": trail,
            "human_handoff_summary": handoff_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Convenience alias for service discovery
HistoryService = HandoffService
