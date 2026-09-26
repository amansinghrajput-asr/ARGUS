"""Conversation history and zero-repeat handoff model schema placeholder."""

from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from pydantic import BaseModel, Field

    class ConversationTurn(BaseModel):
        """Single message turn in the case conversation."""

        turn_id: int
        sender: str  # customer, orchestrator, specialist_agent, human_agent
        message_text: str
        timestamp: Optional[datetime] = None
        detected_intent: Optional[str] = None

    class SpecialistInvestigationNote(BaseModel):
        """Action or finding recorded by an investigation specialist agent."""

        specialist: str  # billing_specialist, technical_specialist, etc.
        action_taken: str
        result: str
        timestamp: Optional[datetime] = None

    class ConversationHistoryBase(BaseModel):
        """Complete conversation memory and investigation record for a case."""

        history_id: str
        case_id: str
        customer_id: str
        messages: List[ConversationTurn] = Field(default_factory=list)
        investigation_trail: List[SpecialistInvestigationNote] = Field(default_factory=list)
        human_handoff_summary: Optional[str] = None

except ImportError:
    class ConversationTurn:  # type: ignore[no-redef]
        def __init__(self, turn_id: int, sender: str, message_text: str) -> None:
            self.turn_id = turn_id
            self.sender = sender
            self.message_text = message_text

    class SpecialistInvestigationNote:  # type: ignore[no-redef]
        def __init__(self, specialist: str, action_taken: str, result: str) -> None:
            self.specialist = specialist
            self.action_taken = action_taken
            self.result = result

    class ConversationHistoryBase:  # type: ignore[no-redef]
        def __init__(self, history_id: str, case_id: str, customer_id: str) -> None:
            self.history_id = history_id
            self.case_id = case_id
            self.customer_id = customer_id
            self.messages: List[ConversationTurn] = []
            self.investigation_trail: List[SpecialistInvestigationNote] = []
            self.human_handoff_summary: Optional[str] = None
