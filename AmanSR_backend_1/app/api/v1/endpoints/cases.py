"""Complaint and Case lifecycle API endpoints implementing ARGUS Case domain contracts."""

from typing import Any, Dict, List, Optional

from ....core.database import get_database
from ....core.exceptions import ArgusDomainError, DuplicateEntityError, EntityNotFoundError, ValidationError
from ....models.case import CaseCreate, CaseResponse, CaseUpdate
from ....repositories.case_repo import CaseRepository
from ....repositories.customer_repo import CustomerRepository
from ....repositories.order_repo import OrderRepository
from ....services.case_service import CaseService

# Shared service instance provider
_shared_case_service: Optional[CaseService] = None


def get_case_service() -> CaseService:
    """Dependency provider for CaseService."""
    global _shared_case_service
    if _shared_case_service is None:
        db = get_database()
        case_repo = CaseRepository(db=db)
        customer_repo = CustomerRepository(db=db)
        order_repo = OrderRepository(db=db)
        _shared_case_service = CaseService(
            case_repo=case_repo,
            customer_repo=customer_repo,
            order_repo=order_repo,
        )
    return _shared_case_service


def reset_case_service(service: Optional[CaseService] = None) -> None:
    """Reset shared service instance for testing isolation."""
    global _shared_case_service
    _shared_case_service = service


try:
    from fastapi import APIRouter, Depends, HTTPException, Query, status

    router = APIRouter(prefix="/cases", tags=["cases"])

    @router.post(
        "",
        response_model=CaseResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new complaint case",
    )
    async def create_case(
        payload: CaseCreate,
        service: CaseService = Depends(get_case_service),
    ) -> Any:
        """Ingest and persist a new customer complaint case."""
        try:
            return await service.create_case(payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except DuplicateEntityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "",
        response_model=List[CaseResponse],
        status_code=status.HTTP_200_OK,
        summary="List complaint cases",
    )
    async def list_cases(
        customer_id: Optional[str] = Query(default=None, description="Filter by customer ID"),
        status: Optional[str] = Query(default=None, description="Filter by case status"),
        limit: int = Query(default=50, ge=1, le=100, description="Max cases to return"),
        service: CaseService = Depends(get_case_service),
        **kwargs: Any,
    ) -> Any:
        """List cases with optional customer and status filters."""
        status_filter = status if status is not None else kwargs.get("status_filter")
        try:
            return await service.list_cases(customer_id=customer_id, status=status_filter, limit=limit)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/{case_id}",
        response_model=CaseResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve case details by case_id",
    )
    async def get_case(
        case_id: str,
        service: CaseService = Depends(get_case_service),
    ) -> Any:
        """Retrieve full case details and triage status."""
        try:
            return await service.get_case(case_id=case_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.patch(
        "/{case_id}",
        response_model=CaseResponse,
        status_code=status.HTTP_200_OK,
        summary="Partially update a complaint case",
    )
    async def update_case(
        case_id: str,
        payload: CaseUpdate,
        service: CaseService = Depends(get_case_service),
    ) -> Any:
        """Update allowed complaint case fields (status, priority, agent, resolution)."""
        try:
            return await service.update_case(case_id=case_id, update_input=payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

except ImportError:
    # Standalone mock router for environments where FastAPI is not yet installed
    class MockCaseRouter:
        def __init__(self) -> None:
            self.routes = [
                ("POST", "/api/v1/cases"),
                ("GET", "/api/v1/cases"),
                ("GET", "/api/v1/cases/{case_id}"),
                ("PATCH", "/api/v1/cases/{case_id}"),
            ]

        async def create_case(self, payload: Any, service: Optional[CaseService] = None) -> Any:
            svc = service or get_case_service()
            return await svc.create_case(payload)

        async def get_case(self, case_id: str, service: Optional[CaseService] = None) -> Any:
            svc = service or get_case_service()
            return await svc.get_case(case_id=case_id)

        async def update_case(self, case_id: str, payload: Any, service: Optional[CaseService] = None) -> Any:
            svc = service or get_case_service()
            return await svc.update_case(case_id=case_id, update_input=payload)

        async def list_cases(
            self,
            customer_id: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 50,
            service: Optional[CaseService] = None,
            **kwargs: Any,
        ) -> Any:
            st = status if status is not None else kwargs.get("status_filter")
            svc = service or get_case_service()
            return await svc.list_cases(customer_id=customer_id, status=st, limit=limit)

    router = MockCaseRouter()  # type: ignore[assignment]
