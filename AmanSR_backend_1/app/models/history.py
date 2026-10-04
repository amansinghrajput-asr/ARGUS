"""Conversation history and zero-repeat human handoff domain models and schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


def validate_turn_fields(sender: str, message_text: str) -> None:
    """Validate conversation turn required fields."""
    if not sender or not str(sender).strip():
        raise ValueError("Turn 'sender' (or role) must not be empty.")
    if not message_text or not str(message_text).strip():
        raise ValueError("Turn 'message_text' (or content) must not be empty.")


def validate_note_fields(specialist: str, action_taken: str, result: str) -> None:
    """Validate specialist investigation note required fields."""
    if not specialist or not str(specialist).strip():
        raise ValueError("Investigation note 'specialist' must not be empty.")
    if not action_taken or not str(action_taken).strip():
        raise ValueError("Investigation note 'action_taken' must not be empty.")
    if not result or not str(result).strip():
        raise ValueError("Investigation note 'result' must not be empty.")


try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    class ConversationTurn(BaseModel):
        """Single message turn in the case conversation."""

        turn_id: int = Field(default=1, description="Sequential turn index")
        sender: str = Field(..., min_length=1, description="Speaker role: customer, orchestrator, specialist_agent, human_agent")
        message_text: str = Field(..., min_length=1, description="Text body of the message")
        timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        detected_intent: Optional[str] = Field(default=None, description="Optional detected user intent")

        @model_validator(mode="before")
        @classmethod
        def handle_aliases(cls, data: Any) -> Any:
            if isinstance(data, dict):
                if "sender" not in data and "role" in data:
                    data["sender"] = data["role"]
                elif "sender" not in data and "speaker" in data:
                    data["sender"] = data["speaker"]
                if "message_text" not in data and "message" in data:
                    data["message_text"] = data["message"]
                elif "message_text" not in data and "content" in data:
                    data["message_text"] = data["content"]
            return data

    class TurnCreate(BaseModel):
        """Request schema for appending a conversation turn."""

        sender: str = Field(..., min_length=1, description="Speaker role")
        message_text: str = Field(..., min_length=1, description="Message text")
        turn_id: Optional[int] = Field(default=None, description="Optional sequential turn identifier")
        timestamp: Optional[str] = Field(default=None, description="Optional ISO timestamp")
        detected_intent: Optional[str] = Field(default=None, description="Optional intent tag")

        @model_validator(mode="before")
        @classmethod
        def handle_aliases(cls, data: Any) -> Any:
            if isinstance(data, dict):
                if "sender" not in data and "role" in data:
                    data["sender"] = data["role"]
                elif "sender" not in data and "speaker" in data:
                    data["sender"] = data["speaker"]
                if "message_text" not in data and "message" in data:
                    data["message_text"] = data["message"]
                elif "message_text" not in data and "content" in data:
                    data["message_text"] = data["content"]
            return data

        @field_validator("sender")
        @classmethod
        def validate_sender(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Turn 'sender' must not be empty.")
            return v.strip()

        @field_validator("message_text")
        @classmethod
        def validate_message(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Turn 'message_text' must not be empty.")
            return v.strip()

    class SpecialistInvestigationNote(BaseModel):
        """Action or finding recorded in the investigation trail."""

        specialist: str = Field(..., min_length=1, description="Specialist agent identifier or name")
        action_taken: str = Field(..., min_length=1, description="Investigation action executed")
        result: str = Field(..., min_length=1, description="Outcome or findings of the action")
        timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

        @model_validator(mode="before")
        @classmethod
        def handle_aliases(cls, data: Any) -> Any:
            if isinstance(data, dict):
                if "specialist" not in data and "agent" in data:
                    data["specialist"] = data["agent"]
                if "action_taken" not in data and "note" in data:
                    data["action_taken"] = data["note"]
                if "result" not in data and "details" in data:
                    data["result"] = data["details"]
            return data

    class NoteCreate(BaseModel):
        """Request schema for appending an investigation note."""

        specialist: str = Field(..., min_length=1, description="Specialist identifier")
        action_taken: str = Field(..., min_length=1, description="Action taken")
        result: str = Field(..., min_length=1, description="Result or observation")
        timestamp: Optional[str] = Field(default=None, description="Optional ISO timestamp")

        @model_validator(mode="before")
        @classmethod
        def handle_aliases(cls, data: Any) -> Any:
            if isinstance(data, dict):
                if "specialist" not in data and "agent" in data:
                    data["specialist"] = data["agent"]
                if "action_taken" not in data and "note" in data:
                    data["action_taken"] = data["note"]
                if "result" not in data and "details" in data:
                    data["result"] = data["details"]
            return data

        @field_validator("specialist")
        @classmethod
        def validate_specialist(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Note 'specialist' must not be empty.")
            return v.strip()

        @field_validator("action_taken")
        @classmethod
        def validate_action(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Note 'action_taken' must not be empty.")
            return v.strip()

        @field_validator("result")
        @classmethod
        def validate_result(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Note 'result' must not be empty.")
            return v.strip()

    class ConversationHistoryResponse(BaseModel):
        """Full conversation memory and investigation record for a complaint case."""

        history_id: str
        case_id: str
        customer_id: str
        messages: List[ConversationTurn] = Field(default_factory=list)
        investigation_trail: List[SpecialistInvestigationNote] = Field(default_factory=list)
        human_handoff_summary: Optional[str] = None
        created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class HumanHandoffResponse(BaseModel):
        """Zero-repeat human handoff packet schema."""

        case_id: str
        case_number: Optional[str] = None
        customer_id: str
        customer_name: Optional[str] = None
        customer_email: Optional[str] = None
        raw_complaint: Optional[str] = None
        category: Optional[str] = None
        priority: Optional[str] = None
        status: Optional[str] = None
        order_id: Optional[str] = None
        confidence_score: Optional[float] = None
        resolution_summary: Optional[str] = None
        escalation_reason: Optional[str] = None
        assigned_agent: Optional[str] = None
        conversation_turns: List[ConversationTurn] = Field(default_factory=list)
        investigation_trail: List[SpecialistInvestigationNote] = Field(default_factory=list)
        human_handoff_summary: str
        generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class ConversationHistoryBase(ConversationHistoryResponse):
        """Base model representation for scaffolding backward compatibility."""
        pass

except ImportError:
    class ConversationTurn:  # type: ignore[no-redef]
        """Fallback schema for conversation message turn."""

        def __init__(
            self,
            turn_id: int = 1,
            sender: Optional[str] = None,
            message_text: Optional[str] = None,
            role: Optional[str] = None,
            speaker: Optional[str] = None,
            message: Optional[str] = None,
            content: Optional[str] = None,
            timestamp: Optional[str] = None,
            detected_intent: Optional[str] = None,
        ) -> None:
            final_sender = sender or role or speaker or ""
            final_message = message_text or message or content or ""
            validate_turn_fields(final_sender, final_message)
            self.turn_id = int(turn_id)
            self.sender = str(final_sender).strip()
            self.message_text = str(final_message).strip()
            self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
            self.detected_intent = str(detected_intent).strip() if detected_intent else None

        @property
        def role(self) -> str:
            return self.sender

        @property
        def content(self) -> str:
            return self.message_text

        def to_dict(self) -> Dict[str, Any]:
            return {
                "turn_id": self.turn_id,
                "sender": self.sender,
                "message_text": self.message_text,
                "timestamp": self.timestamp,
                "detected_intent": self.detected_intent,
            }

    class TurnCreate:  # type: ignore[no-redef]
        def __init__(
            self,
            sender: Optional[str] = None,
            message_text: Optional[str] = None,
            turn_id: Optional[int] = None,
            role: Optional[str] = None,
            speaker: Optional[str] = None,
            message: Optional[str] = None,
            content: Optional[str] = None,
            timestamp: Optional[str] = None,
            detected_intent: Optional[str] = None,
        ) -> None:
            final_sender = sender or role or speaker or ""
            final_message = message_text or message or content or ""
            validate_turn_fields(final_sender, final_message)
            self.sender = str(final_sender).strip()
            self.message_text = str(final_message).strip()
            self.turn_id = int(turn_id) if turn_id is not None else None
            self.timestamp = timestamp
            self.detected_intent = detected_intent

        def to_dict(self) -> Dict[str, Any]:
            return {
                "sender": self.sender,
                "message_text": self.message_text,
                "turn_id": self.turn_id,
                "timestamp": self.timestamp,
                "detected_intent": self.detected_intent,
            }

    class SpecialistInvestigationNote:  # type: ignore[no-redef]
        """Fallback schema for specialist investigation note."""

        def __init__(
            self,
            specialist: Optional[str] = None,
            action_taken: Optional[str] = None,
            result: Optional[str] = None,
            agent: Optional[str] = None,
            note: Optional[str] = None,
            details: Optional[str] = None,
            timestamp: Optional[str] = None,
        ) -> None:
            final_specialist = specialist or agent or ""
            final_action = action_taken or note or ""
            final_result = result or details or ""
            validate_note_fields(final_specialist, final_action, final_result)
            self.specialist = str(final_specialist).strip()
            self.action_taken = str(final_action).strip()
            self.result = str(final_result).strip()
            self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        def to_dict(self) -> Dict[str, Any]:
            return {
                "specialist": self.specialist,
                "action_taken": self.action_taken,
                "result": self.result,
                "timestamp": self.timestamp,
            }

    class NoteCreate:  # type: ignore[no-redef]
        def __init__(
            self,
            specialist: Optional[str] = None,
            action_taken: Optional[str] = None,
            result: Optional[str] = None,
            agent: Optional[str] = None,
            note: Optional[str] = None,
            details: Optional[str] = None,
            timestamp: Optional[str] = None,
        ) -> None:
            final_spec = specialist or agent or ""
            final_act = action_taken or note or ""
            final_res = result or details or ""
            validate_note_fields(final_spec, final_act, final_res)
            self.specialist = str(final_spec).strip()
            self.action_taken = str(final_act).strip()
            self.result = str(final_res).strip()
            self.timestamp = timestamp

        def to_dict(self) -> Dict[str, Any]:
            return {
                "specialist": self.specialist,
                "action_taken": self.action_taken,
                "result": self.result,
                "timestamp": self.timestamp,
            }

    class ConversationHistoryResponse:  # type: ignore[no-redef]
        def __init__(
            self,
            history_id: str,
            case_id: str,
            customer_id: str,
            messages: Optional[List[Any]] = None,
            investigation_trail: Optional[List[Any]] = None,
            human_handoff_summary: Optional[str] = None,
            created_at: Optional[str] = None,
            updated_at: Optional[str] = None,
        ) -> None:
            self.history_id = history_id
            self.case_id = case_id
            self.customer_id = customer_id
            self.messages = messages or []
            self.investigation_trail = investigation_trail or []
            self.human_handoff_summary = human_handoff_summary
            now_iso = datetime.now(timezone.utc).isoformat()
            self.created_at = created_at or now_iso
            self.updated_at = updated_at or now_iso

        def to_dict(self) -> Dict[str, Any]:
            return {
                "history_id": self.history_id,
                "case_id": self.case_id,
                "customer_id": self.customer_id,
                "messages": [m.to_dict() if hasattr(m, "to_dict") else m for m in self.messages],
                "investigation_trail": [n.to_dict() if hasattr(n, "to_dict") else n for n in self.investigation_trail],
                "human_handoff_summary": self.human_handoff_summary,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    class HumanHandoffResponse:  # type: ignore[no-redef]
        def __init__(
            self,
            case_id: str,
            customer_id: str,
            human_handoff_summary: str,
            case_number: Optional[str] = None,
            customer_name: Optional[str] = None,
            customer_email: Optional[str] = None,
            raw_complaint: Optional[str] = None,
            category: Optional[str] = None,
            priority: Optional[str] = None,
            status: Optional[str] = None,
            order_id: Optional[str] = None,
            confidence_score: Optional[float] = None,
            resolution_summary: Optional[str] = None,
            escalation_reason: Optional[str] = None,
            assigned_agent: Optional[str] = None,
            conversation_turns: Optional[List[Any]] = None,
            investigation_trail: Optional[List[Any]] = None,
            generated_at: Optional[str] = None,
        ) -> None:
            self.case_id = case_id
            self.customer_id = customer_id
            self.human_handoff_summary = human_handoff_summary
            self.case_number = case_number
            self.customer_name = customer_name
            self.customer_email = customer_email
            self.raw_complaint = raw_complaint
            self.category = category
            self.priority = priority
            self.status = status
            self.order_id = order_id
            self.confidence_score = confidence_score
            self.resolution_summary = resolution_summary
            self.escalation_reason = escalation_reason
            self.assigned_agent = assigned_agent
            self.conversation_turns = conversation_turns or []
            self.investigation_trail = investigation_trail or []
            self.generated_at = generated_at or datetime.now(timezone.utc).isoformat()

        def to_dict(self) -> Dict[str, Any]:
            return {
                "case_id": self.case_id,
                "case_number": self.case_number,
                "customer_id": self.customer_id,
                "customer_name": self.customer_name,
                "customer_email": self.customer_email,
                "raw_complaint": self.raw_complaint,
                "category": self.category,
                "priority": self.priority,
                "status": self.status,
                "order_id": self.order_id,
                "confidence_score": self.confidence_score,
                "resolution_summary": self.resolution_summary,
                "escalation_reason": self.escalation_reason,
                "assigned_agent": self.assigned_agent,
                "conversation_turns": [t.to_dict() if hasattr(t, "to_dict") else t for t in self.conversation_turns],
                "investigation_trail": [n.to_dict() if hasattr(n, "to_dict") else n for n in self.investigation_trail],
                "human_handoff_summary": self.human_handoff_summary,
                "generated_at": self.generated_at,
            }

    class ConversationHistoryBase(ConversationHistoryResponse):  # type: ignore[no-redef]
        pass
