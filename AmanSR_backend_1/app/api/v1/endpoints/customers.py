"""Customer API endpoints implementing ARGUS Customer domain contracts."""

from typing import Any, Dict, Optional

from ....core.database import get_database
from ....core.exceptions import ArgusDomainError, DuplicateEntityError, EntityNotFoundError, ValidationError
from ....models.customer import CustomerCreate, CustomerResponse
from ....repositories.customer_repo import CustomerRepository
from ....services.customer_service import CustomerService

# Shared service instance provider
_shared_customer_service: Optional[CustomerService] = None


def get_customer_service() -> CustomerService:
    """Dependency provider for CustomerService."""
    global _shared_customer_service
    if _shared_customer_service is None:
        db = get_database()
        repo = CustomerRepository(db=db)
        _shared_customer_service = CustomerService(customer_repo=repo)
    return _shared_customer_service


def reset_customer_service(service: Optional[CustomerService] = None) -> None:
    """Reset shared service instance for testing isolation."""
    global _shared_customer_service
    _shared_customer_service = service


try:
    from fastapi import APIRouter, Depends, HTTPException, Query, status

    router = APIRouter(prefix="/customers", tags=["customers"])

    @router.post(
        "",
        response_model=CustomerResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new customer profile",
    )
    async def create_customer(
        payload: CustomerCreate,
        service: CustomerService = Depends(get_customer_service),
    ) -> Any:
        """Create and register a new customer profile."""
        try:
            return await service.create_customer(payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except DuplicateEntityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/lookup",
        response_model=CustomerResponse,
        status_code=status.HTTP_200_OK,
        summary="Lookup customer by email or phone",
    )
    async def lookup_customer(
        email: Optional[str] = Query(default=None, description="Exact email address"),
        phone: Optional[str] = Query(default=None, description="Exact phone number"),
        service: CustomerService = Depends(get_customer_service),
    ) -> Any:
        """Lookup customer by email or phone identifier."""
        try:
            return await service.lookup_customer(email=email, phone=phone)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/{customer_id}",
        response_model=CustomerResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve customer by customer_id",
    )
    async def get_customer(
        customer_id: str,
        service: CustomerService = Depends(get_customer_service),
    ) -> Any:
        """Retrieve customer details by unique customer_id."""
        try:
            return await service.get_customer(customer_id=customer_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

except ImportError:
    # Standalone mock router for environments where FastAPI is not yet installed
    class MockCustomerRouter:
        def __init__(self) -> None:
            self.routes = [
                ("POST", "/api/v1/customers"),
                ("GET", "/api/v1/customers/lookup"),
                ("GET", "/api/v1/customers/{customer_id}"),
            ]

        async def create_customer(self, payload: Any, service: Optional[CustomerService] = None) -> Any:
            svc = service or get_customer_service()
            return await svc.create_customer(payload)

        async def lookup_customer(
            self,
            email: Optional[str] = None,
            phone: Optional[str] = None,
            service: Optional[CustomerService] = None,
        ) -> Any:
            svc = service or get_customer_service()
            return await svc.lookup_customer(email=email, phone=phone)

        async def get_customer(self, customer_id: str, service: Optional[CustomerService] = None) -> Any:
            svc = service or get_customer_service()
            return await svc.get_customer(customer_id=customer_id)

    router = MockCustomerRouter()  # type: ignore[assignment]
