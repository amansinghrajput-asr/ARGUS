"""Complaint and Case lifecycle domain model schema placeholder."""

from typing import List, Optional
from datetime import datetime

try:
    from pydantic import BaseModel, Field

    class ComplaintCaseBase(BaseModel):
        """Minimal schema for ComplaintCase entity."""

        case_id: str
        case_number: str
        customer_id: str
        order_id: Optional[str] = None
        raw_complaint_text: str
        parsed_sub_issues: List[str] = Field(default_factory=list)
        category: str = "general"  # billing, order_fulfillment, technical, account, general
        priority: str = "medium"  # low, medium, high, critical
        status: str = "open"  # open, investigating, resolved_ai, escalated_to_human, closed
        confidence_score: Optional[float] = None
        resolution_summary: Optional[str] = None
        escalation_reason: Optional[str] = None
        assigned_agent: Optional[str] = None
        created_at: Optional[datetime] = None

except ImportError:
    class ComplaintCaseBase:  # type: ignore[no-redef]
        def __init__(
            self,
            case_id: str,
            case_number: str,
            customer_id: str,
            raw_complaint_text: str,
            order_id: Optional[str] = None,
            category: str = "general",
            priority: str = "medium",
            status: str = "open",
        ) -> None:
            self.case_id = case_id
            self.case_number = case_number
            self.customer_id = customer_id
            self.order_id = order_id
            self.raw_complaint_text = raw_complaint_text
            self.category = category
            self.priority = priority
            self.status = status
            self.parsed_sub_issues: List[str] = []
