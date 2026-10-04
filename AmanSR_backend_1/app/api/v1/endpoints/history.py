"""Conversation history and zero-repeat human handoff API endpoints."""

from typing import Any, Dict, List, Optional

from ....core.database import get_database
from ....core.exceptions import ArgusDomainError, EntityNotFoundError, ValidationError
from ....models.history import (
    ConversationHistoryResponse,
    HumanHandoffResponse,
    NoteCreate,
    TurnCreate,
)
from ....repositories.case_repo import CaseRepository
from ....repositories.customer_repo import CustomerRepository
from ....repositories.history_repo import HistoryRepository
from ....repositories.order_repo import OrderRepository
from ....services.handoff_service import HandoffService

# Shared service instance provider
_shared_handoff_service: Optional[HandoffService] = None


def get_handoff_service() -> HandoffService:
    """Dependency provider for HandoffService / HistoryService."""
    global _shared_handoff_service
    if _shared_handoff_service is None:
        db = get_database()
        history_repo = HistoryRepository(db=db)
        case_repo = CaseRepository(db=db)
        customer_repo = CustomerRepository(db=db)
        order_repo = OrderRepository(db=db)
        _shared_handoff_service = HandoffService(
            history_repo=history_repo,
            case_repo=case_repo,
            customer_repo=customer_repo,
            order_repo=order_repo,
        )
    return _shared_handoff_service


def reset_handoff_service(service: Optional[HandoffService] = None) -> None:
    """Reset shared service instance for testing isolation."""
    global _shared_handoff_service
    _shared_handoff_service = service


try:
    from fastapi import APIRouter, Depends, HTTPException, status

    router = APIRouter(prefix="/cases", tags=["history"])

    @router.get(
        "/{case_id}/history",
        response_model=ConversationHistoryResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve case conversation history",
    )
    async def get_case_history(
        case_id: str,
        service: HandoffService = Depends(get_handoff_service),
    ) -> Any:
        """Retrieve full conversation memory and specialist investigation trail for a case."""
        try:
            return await service.get_history(case_id=case_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.post(
        "/{case_id}/history/turns",
        response_model=ConversationHistoryResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Append a conversation message turn",
    )
    async def add_conversation_turn(
        case_id: str,
        payload: TurnCreate,
        service: HandoffService = Depends(get_handoff_service),
    ) -> Any:
        """Append a message turn to the case conversation history."""
        try:
            return await service.add_turn(case_id=case_id, turn_input=payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.post(
        "/{case_id}/history/notes",
        response_model=ConversationHistoryResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Append an investigation note",
    )
    async def add_investigation_note(
        case_id: str,
        payload: NoteCreate,
        service: HandoffService = Depends(get_handoff_service),
    ) -> Any:
        """Append a specialist finding or investigation action to the case trail."""
        try:
            return await service.add_note(case_id=case_id, note_input=payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/{case_id}/handoff",
        response_model=HumanHandoffResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve zero-repeat human handoff packet",
    )
    async def get_human_handoff(
        case_id: str,
        service: HandoffService = Depends(get_handoff_service),
    ) -> Any:
        """Assemble and return structured context packet for zero-repeat human agent handoff."""
        try:
            return await service.compile_handoff_packet(case_id=case_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

except ImportError:
    # Standalone mock router for environments where FastAPI is not yet installed
    class MockCaseHistoryRouter:
        def __init__(self) -> None:
            self.routes = [
                ("GET", "/api/v1/cases/{case_id}/history"),
                ("POST", "/api/v1/cases/{case_id}/history/turns"),
                ("POST", "/api/v1/cases/{case_id}/history/notes"),
                ("GET", "/api/v1/cases/{case_id}/handoff"),
            ]

        async def get_case_history(self, case_id: str, service: Optional[HandoffService] = None) -> Any:
            svc = service or get_handoff_service()
            return await svc.get_history(case_id=case_id)

        async def add_conversation_turn(self, case_id: str, payload: Any, service: Optional[HandoffService] = None) -> Any:
            svc = service or get_handoff_service()
            return await svc.add_turn(case_id=case_id, turn_input=payload)

        async def add_investigation_note(self, case_id: str, payload: Any, service: Optional[HandoffService] = None) -> Any:
            svc = service or get_handoff_service()
            return await svc.add_note(case_id=case_id, note_input=payload)

        async def get_human_handoff(self, case_id: str, service: Optional[HandoffService] = None) -> Any:
            svc = service or get_handoff_service()
            return await svc.compile_handoff_packet(case_id=case_id)

    router = MockCaseHistoryRouter()  # type: ignore[assignment]
