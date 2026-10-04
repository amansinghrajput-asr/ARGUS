"""ComplaintCase lifecycle business logic and service layer."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError
from ..models.case import VALID_CASE_STATUSES, VALID_PRIORITIES, validate_case_fields
from ..repositories.case_repo import CaseRepository
from ..repositories.customer_repo import CustomerRepository
from ..repositories.order_repo import OrderRepository


class CaseService:
    """Encapsulates business rules and state management for the ComplaintCase domain."""

    def __init__(
        self,
        case_repo: Optional[CaseRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
        order_repo: Optional[OrderRepository] = None,
    ) -> None:
        self.case_repo = case_repo or CaseRepository()
        self.customer_repo = customer_repo
        self.order_repo = order_repo

    async def create_case(
        self,
        case_input: Union[Dict[str, Any], Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Validate, verify references, and persist a new complaint case."""
        data: Dict[str, Any] = {}
        if case_input is not None:
            if hasattr(case_input, "to_dict"):
                data = case_input.to_dict()
            elif hasattr(case_input, "model_dump"):
                data = case_input.model_dump()
            elif isinstance(case_input, dict):
                data = dict(case_input)
        if kwargs:
            data.update(kwargs)

        customer_id = data.get("customer_id", "")
        raw_complaint = data.get("raw_complaint") or data.get("raw_complaint_text") or ""
        order_id = data.get("order_id")
        status = data.get("status", "open")
        priority = data.get("priority", "medium")
        category = data.get("category", "general")
        confidence_score = data.get("confidence_score")
        parsed_sub_issues = data.get("parsed_sub_issues", [])
        assigned_agent = data.get("assigned_agent")
        resolution_summary = data.get("resolution_summary")
        escalation_reason = data.get("escalation_reason")

        # 1. Domain schema validation
        try:
            validate_case_fields(
                customer_id=customer_id,
                raw_complaint=raw_complaint,
                status=status,
                priority=priority,
                category=category,
                confidence_score=confidence_score,
            )
        except ValueError as e:
            raise ValidationError(str(e))

        clean_customer_id = str(customer_id).strip()
        clean_raw_complaint = str(raw_complaint).strip()
        clean_status = str(status).strip().lower()
        clean_priority = str(priority).strip().lower()
        clean_category = str(category).strip().lower() if category else "general"

        # 2. Verify referenced customer existence
        if self.customer_repo is not None:
            customer = await self.customer_repo.get_by_id(clean_customer_id)
            if customer is None:
                raise EntityNotFoundError(f"Customer with ID '{clean_customer_id}' was not found.")

        # 3. Verify referenced order existence (if provided)
        clean_order_id: Optional[str] = None
        if order_id and str(order_id).strip():
            clean_order_id = str(order_id).strip()
            if self.order_repo is not None:
                order = await self.order_repo.get_by_id(clean_order_id)
                if order is None:
                    raise EntityNotFoundError(f"Order with ID '{clean_order_id}' was not found.")

        # 4. Handle unique case_id and case_number
        case_id = data.get("case_id")
        if not case_id or not str(case_id).strip():
            case_id = f"case_{uuid.uuid4().hex[:10]}"
        else:
            case_id = str(case_id).strip()

        case_number = data.get("case_number")
        if not case_number or not str(case_number).strip():
            case_number = f"ARG-{uuid.uuid4().hex[:6].upper()}"
        else:
            case_number = str(case_number).strip()

        # Check collision
        existing_case = await self.case_repo.get_by_id(case_id)
        if existing_case is not None:
            raise DuplicateEntityError(f"Case with ID '{case_id}' already exists.")

        # 5. Build canonical case document
        now_iso = datetime.now(timezone.utc).isoformat()
        case_record: Dict[str, Any] = {
            "case_id": case_id,
            "case_number": case_number,
            "customer_id": clean_customer_id,
            "order_id": clean_order_id,
            "raw_complaint": clean_raw_complaint,
            "parsed_sub_issues": list(parsed_sub_issues) if parsed_sub_issues else [],
            "category": clean_category,
            "priority": clean_priority,
            "status": clean_status,
            "confidence_score": float(confidence_score) if confidence_score is not None else None,
            "resolution_summary": str(resolution_summary).strip() if resolution_summary else None,
            "escalation_reason": str(escalation_reason).strip() if escalation_reason else None,
            "assigned_agent": str(assigned_agent).strip() if assigned_agent else None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # 6. Persist record
        return await self.case_repo.create(case_record)

    async def get_case(self, case_id: str) -> Dict[str, Any]:
        """Retrieve complaint case by unique case_id."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        clean_id = str(case_id).strip()
        case = await self.case_repo.get_by_id(clean_id)
        if case is None:
            raise EntityNotFoundError(f"Case with ID '{clean_id}' was not found.")
        return case

    async def update_case(
        self,
        case_id: str,
        update_input: Union[Dict[str, Any], Any],
    ) -> Dict[str, Any]:
        """Apply partial update (PATCH) to an existing complaint case."""
        if not case_id or not str(case_id).strip():
            raise ValidationError("Invalid case_id provided.")

        clean_id = str(case_id).strip()
        existing = await self.case_repo.get_by_id(clean_id)
        if existing is None:
            raise EntityNotFoundError(f"Case with ID '{clean_id}' was not found.")

        data: Dict[str, Any] = (
            update_input.to_dict()
            if hasattr(update_input, "to_dict")
            else dict(update_input)
            if not hasattr(update_input, "model_dump")
            else update_input.model_dump(exclude_unset=True)
        )

        update_fields: Dict[str, Any] = {}

        # Validate allowed updatable fields
        if "status" in data and data["status"] is not None:
            status_clean = str(data["status"]).strip().lower()
            if status_clean not in VALID_CASE_STATUSES:
                raise ValidationError(
                    f"Invalid case status '{data['status']}'. Must be one of: {', '.join(sorted(VALID_CASE_STATUSES))}."
                )
            update_fields["status"] = status_clean

        if "priority" in data and data["priority"] is not None:
            priority_clean = str(data["priority"]).strip().lower()
            if priority_clean not in VALID_PRIORITIES:
                raise ValidationError(
                    f"Invalid priority '{data['priority']}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
                )
            update_fields["priority"] = priority_clean

        if "category" in data and data["category"] is not None:
            update_fields["category"] = str(data["category"]).strip().lower()

        if "parsed_sub_issues" in data and data["parsed_sub_issues"] is not None:
            if not isinstance(data["parsed_sub_issues"], list):
                raise ValidationError("Field 'parsed_sub_issues' must be a list.")
            update_fields["parsed_sub_issues"] = data["parsed_sub_issues"]

        if "confidence_score" in data:
            score = data["confidence_score"]
            if score is not None:
                if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                    raise ValidationError("Field 'confidence_score' must be a number between 0.0 and 1.0.")
                update_fields["confidence_score"] = float(score)
            else:
                update_fields["confidence_score"] = None

        if "resolution_summary" in data:
            update_fields["resolution_summary"] = str(data["resolution_summary"]).strip() if data["resolution_summary"] else None

        if "escalation_reason" in data:
            update_fields["escalation_reason"] = str(data["escalation_reason"]).strip() if data["escalation_reason"] else None

        if "assigned_agent" in data:
            update_fields["assigned_agent"] = str(data["assigned_agent"]).strip() if data["assigned_agent"] else None

        if "order_id" in data:
            new_order_id = str(data["order_id"]).strip() if data["order_id"] else None
            if new_order_id and self.order_repo is not None:
                order = await self.order_repo.get_by_id(new_order_id)
                if order is None:
                    raise EntityNotFoundError(f"Order with ID '{new_order_id}' was not found.")
            update_fields["order_id"] = new_order_id

        if not update_fields:
            return existing

        updated = await self.case_repo.update(clean_id, update_fields)
        if updated is None:
            raise EntityNotFoundError(f"Case with ID '{clean_id}' was not found.")
        return updated

    async def list_cases(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List cases with optional customer_id and status filters."""
        clean_cust_id: Optional[str] = None
        if customer_id and str(customer_id).strip():
            clean_cust_id = str(customer_id).strip()
            if self.customer_repo is not None:
                customer = await self.customer_repo.get_by_id(clean_cust_id)
                if customer is None:
                    raise EntityNotFoundError(f"Customer with ID '{clean_cust_id}' was not found.")

        clean_status = str(status).strip().lower() if status and str(status).strip() else None
        return await self.case_repo.list_cases(customer_id=clean_cust_id, status=clean_status, limit=limit)
