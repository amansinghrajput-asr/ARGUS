"""Complaint and Case lifecycle domain models and request/response schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

VALID_CASE_STATUSES = {"open", "investigating", "resolved_ai", "escalated_to_human", "closed"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_CATEGORIES = {"billing", "order_fulfillment", "technical", "account", "general"}


def validate_case_fields(
    customer_id: str,
    raw_complaint: str,
    status: str = "open",
    priority: str = "medium",
    category: str = "general",
    confidence_score: Optional[float] = None,
) -> None:
    """Validate core ComplaintCase fields."""
    if not customer_id or not str(customer_id).strip():
        raise ValueError("Case 'customer_id' must not be empty.")
    if not raw_complaint or not str(raw_complaint).strip():
        raise ValueError("Case 'raw_complaint' text must not be empty.")
    if status and status.strip().lower() not in VALID_CASE_STATUSES:
        raise ValueError(
            f"Invalid case status '{status}'. Must be one of: {', '.join(sorted(VALID_CASE_STATUSES))}."
        )
    if priority and priority.strip().lower() not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
        )
    if confidence_score is not None:
        if not isinstance(confidence_score, (int, float)) or not (0.0 <= confidence_score <= 1.0):
            raise ValueError("Case 'confidence_score' must be a number between 0.0 and 1.0.")


try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    class CaseCreate(BaseModel):
        """Schema for complaint case ingestion request."""

        customer_id: str = Field(..., min_length=1, description="Associated customer identifier")
        raw_complaint: str = Field(..., min_length=1, description="Raw customer complaint text")
        order_id: Optional[str] = Field(default=None, description="Optional associated order identifier")
        case_id: Optional[str] = Field(default=None, description="Optional custom case ID")
        case_number: Optional[str] = Field(default=None, description="Optional human-readable case number")
        category: str = Field(default="general", description="Issue category")
        priority: str = Field(default="medium", description="Case priority")
        status: str = Field(default="open", description="Lifecycle status")
        parsed_sub_issues: List[Any] = Field(default_factory=list, description="Extracted sub-issues")
        confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Triage confidence")
        assigned_agent: Optional[str] = Field(default=None, description="Assigned human/specialist agent")

        @model_validator(mode="before")
        @classmethod
        def handle_raw_complaint_alias(cls, data: Any) -> Any:
            if isinstance(data, dict):
                if "raw_complaint" not in data and "raw_complaint_text" in data:
                    data["raw_complaint"] = data["raw_complaint_text"]
            return data

        @field_validator("customer_id")
        @classmethod
        def validate_customer_id(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Case 'customer_id' must not be empty.")
            return v.strip()

        @field_validator("raw_complaint")
        @classmethod
        def validate_raw_complaint(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Case 'raw_complaint' text must not be empty.")
            return v.strip()

        @field_validator("status")
        @classmethod
        def validate_status(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_CASE_STATUSES:
                raise ValueError(
                    f"Invalid case status '{v}'. Must be one of: {', '.join(sorted(VALID_CASE_STATUSES))}."
                )
            return v_clean

        @field_validator("priority")
        @classmethod
        def validate_priority(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_PRIORITIES:
                raise ValueError(
                    f"Invalid priority '{v}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
                )
            return v_clean

    class CaseUpdate(BaseModel):
        """Schema for partial update (PATCH) of a complaint case."""

        status: Optional[str] = Field(default=None, description="Updated case status")
        priority: Optional[str] = Field(default=None, description="Updated priority")
        category: Optional[str] = Field(default=None, description="Updated category")
        parsed_sub_issues: Optional[List[Any]] = Field(default=None, description="Updated sub-issues list")
        confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Updated confidence score")
        resolution_summary: Optional[str] = Field(default=None, description="Summary of resolution")
        escalation_reason: Optional[str] = Field(default=None, description="Reason for escalation")
        assigned_agent: Optional[str] = Field(default=None, description="Assigned agent ID")
        order_id: Optional[str] = Field(default=None, description="Associated order ID")

        @field_validator("status")
        @classmethod
        def validate_status(cls, v: Optional[str]) -> Optional[str]:
            if v is not None:
                v_clean = v.strip().lower()
                if v_clean not in VALID_CASE_STATUSES:
                    raise ValueError(
                        f"Invalid case status '{v}'. Must be one of: {', '.join(sorted(VALID_CASE_STATUSES))}."
                    )
                return v_clean
            return v

        @field_validator("priority")
        @classmethod
        def validate_priority(cls, v: Optional[str]) -> Optional[str]:
            if v is not None:
                v_clean = v.strip().lower()
                if v_clean not in VALID_PRIORITIES:
                    raise ValueError(
                        f"Invalid priority '{v}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
                    )
                return v_clean
            return v

    class CaseResponse(BaseModel):
        """Clean API response model for ComplaintCase entity."""

        case_id: str
        case_number: str
        customer_id: str
        order_id: Optional[str] = None
        raw_complaint: str
        parsed_sub_issues: List[Any] = Field(default_factory=list)
        category: str = "general"
        priority: str = "medium"
        status: str = "open"
        confidence_score: Optional[float] = None
        resolution_summary: Optional[str] = None
        escalation_reason: Optional[str] = None
        assigned_agent: Optional[str] = None
        created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

        @property
        def raw_complaint_text(self) -> str:
            """Alias for backward compatibility with scaffolding tests."""
            return self.raw_complaint

    class ComplaintCaseBase(CaseResponse):
        """Base complaint case model representation."""

        def __init__(self, **data: Any) -> None:
            if "raw_complaint" not in data and "raw_complaint_text" in data:
                data["raw_complaint"] = data["raw_complaint_text"]
            super().__init__(**data)

except ImportError:
    class CaseCreate:  # type: ignore[no-redef]
        """Fallback schema for case creation request when pydantic is not installed."""

        def __init__(
            self,
            customer_id: str,
            raw_complaint: Optional[str] = None,
            raw_complaint_text: Optional[str] = None,
            order_id: Optional[str] = None,
            case_id: Optional[str] = None,
            case_number: Optional[str] = None,
            category: str = "general",
            priority: str = "medium",
            status: str = "open",
            parsed_sub_issues: Optional[List[Any]] = None,
            confidence_score: Optional[float] = None,
            assigned_agent: Optional[str] = None,
        ) -> None:
            text = raw_complaint if raw_complaint is not None else raw_complaint_text or ""
            validate_case_fields(
                customer_id=customer_id,
                raw_complaint=text,
                status=status,
                priority=priority,
                category=category,
                confidence_score=confidence_score,
            )
            self.customer_id = str(customer_id).strip()
            self.raw_complaint = str(text).strip()
            self.order_id = str(order_id).strip() if order_id else None
            self.case_id = str(case_id).strip() if case_id else None
            self.case_number = str(case_number).strip() if case_number else None
            self.category = (category or "general").strip().lower()
            self.priority = (priority or "medium").strip().lower()
            self.status = (status or "open").strip().lower()
            self.parsed_sub_issues = parsed_sub_issues or []
            self.confidence_score = float(confidence_score) if confidence_score is not None else None
            self.assigned_agent = str(assigned_agent).strip() if assigned_agent else None

        @property
        def raw_complaint_text(self) -> str:
            return self.raw_complaint

        def to_dict(self) -> Dict[str, Any]:
            return {
                "case_id": self.case_id,
                "case_number": self.case_number,
                "customer_id": self.customer_id,
                "order_id": self.order_id,
                "raw_complaint": self.raw_complaint,
                "parsed_sub_issues": self.parsed_sub_issues,
                "category": self.category,
                "priority": self.priority,
                "status": self.status,
                "confidence_score": self.confidence_score,
                "assigned_agent": self.assigned_agent,
            }

    class CaseUpdate:  # type: ignore[no-redef]
        """Fallback schema for case partial update when pydantic is not installed."""

        def __init__(
            self,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            category: Optional[str] = None,
            parsed_sub_issues: Optional[List[Any]] = None,
            confidence_score: Optional[float] = None,
            resolution_summary: Optional[str] = None,
            escalation_reason: Optional[str] = None,
            assigned_agent: Optional[str] = None,
            order_id: Optional[str] = None,
        ) -> None:
            if status is not None:
                clean_status = status.strip().lower()
                if clean_status not in VALID_CASE_STATUSES:
                    raise ValueError(f"Invalid case status '{status}'.")
                self.status = clean_status
            else:
                self.status = None

            if priority is not None:
                clean_priority = priority.strip().lower()
                if clean_priority not in VALID_PRIORITIES:
                    raise ValueError(f"Invalid priority '{priority}'.")
                self.priority = clean_priority
            else:
                self.priority = None

            if confidence_score is not None:
                if not isinstance(confidence_score, (int, float)) or not (0.0 <= confidence_score <= 1.0):
                    raise ValueError("confidence_score must be between 0.0 and 1.0.")
                self.confidence_score = float(confidence_score)
            else:
                self.confidence_score = None

            self.category = category.strip().lower() if category else None
            self.parsed_sub_issues = parsed_sub_issues
            self.resolution_summary = resolution_summary
            self.escalation_reason = escalation_reason
            self.assigned_agent = assigned_agent
            self.order_id = order_id

        def to_dict(self) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for field in [
                "status", "priority", "category", "parsed_sub_issues",
                "confidence_score", "resolution_summary", "escalation_reason",
                "assigned_agent", "order_id"
            ]:
                val = getattr(self, field, None)
                if val is not None:
                    result[field] = val
            return result

    class CaseResponse:  # type: ignore[no-redef]
        """Fallback case response model."""

        def __init__(
            self,
            case_id: str,
            case_number: str,
            customer_id: str,
            raw_complaint: Optional[str] = None,
            raw_complaint_text: Optional[str] = None,
            order_id: Optional[str] = None,
            parsed_sub_issues: Optional[List[Any]] = None,
            category: str = "general",
            priority: str = "medium",
            status: str = "open",
            confidence_score: Optional[float] = None,
            resolution_summary: Optional[str] = None,
            escalation_reason: Optional[str] = None,
            assigned_agent: Optional[str] = None,
            created_at: Optional[str] = None,
            updated_at: Optional[str] = None,
        ) -> None:
            self.case_id = case_id
            self.case_number = case_number
            self.customer_id = customer_id
            self.order_id = order_id
            self.raw_complaint = raw_complaint if raw_complaint is not None else raw_complaint_text or ""
            self.parsed_sub_issues = parsed_sub_issues or []
            self.category = category
            self.priority = priority
            self.status = status
            self.confidence_score = confidence_score
            self.resolution_summary = resolution_summary
            self.escalation_reason = escalation_reason
            self.assigned_agent = assigned_agent
            now_iso = datetime.now(timezone.utc).isoformat()
            self.created_at = created_at or now_iso
            self.updated_at = updated_at or now_iso

        @property
        def raw_complaint_text(self) -> str:
            return self.raw_complaint

        def to_dict(self) -> Dict[str, Any]:
            return {
                "case_id": self.case_id,
                "case_number": self.case_number,
                "customer_id": self.customer_id,
                "order_id": self.order_id,
                "raw_complaint": self.raw_complaint,
                "parsed_sub_issues": self.parsed_sub_issues,
                "category": self.category,
                "priority": self.priority,
                "status": self.status,
                "confidence_score": self.confidence_score,
                "resolution_summary": self.resolution_summary,
                "escalation_reason": self.escalation_reason,
                "assigned_agent": self.assigned_agent,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    class ComplaintCaseBase(CaseResponse):  # type: ignore[no-redef]
        pass
