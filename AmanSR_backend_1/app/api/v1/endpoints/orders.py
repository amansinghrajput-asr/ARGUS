"""Order API endpoints implementing ARGUS Order domain contracts."""

from typing import Any, Dict, List, Optional

from ....core.database import get_database
from ....core.exceptions import ArgusDomainError, DuplicateEntityError, EntityNotFoundError, ValidationError
from ....models.order import OrderCreate, OrderResponse
from ....repositories.customer_repo import CustomerRepository
from ....repositories.order_repo import OrderRepository
from ....services.order_service import OrderService

# Shared service instance provider
_shared_order_service: Optional[OrderService] = None


def get_order_service() -> OrderService:
    """Dependency provider for OrderService."""
    global _shared_order_service
    if _shared_order_service is None:
        db = get_database()
        order_repo = OrderRepository(db=db)
        customer_repo = CustomerRepository(db=db)
        _shared_order_service = OrderService(order_repo=order_repo, customer_repo=customer_repo)
    return _shared_order_service


def reset_order_service(service: Optional[OrderService] = None) -> None:
    """Reset shared service instance for testing isolation."""
    global _shared_order_service
    _shared_order_service = service


try:
    from fastapi import APIRouter, Depends, HTTPException, status

    router = APIRouter(tags=["orders"])

    @router.post(
        "/orders",
        response_model=OrderResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new order",
    )
    async def create_order(
        payload: OrderCreate,
        service: OrderService = Depends(get_order_service),
    ) -> Any:
        """Create and persist a new order record."""
        try:
            return await service.create_order(payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except DuplicateEntityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/orders/{order_id}",
        response_model=OrderResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve order by order_id",
    )
    async def get_order(
        order_id: str,
        service: OrderService = Depends(get_order_service),
    ) -> Any:
        """Retrieve order details by unique order_id."""
        try:
            return await service.get_order(order_id=order_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/customers/{customer_id}/orders",
        response_model=List[OrderResponse],
        status_code=status.HTTP_200_OK,
        summary="Retrieve all orders for a customer",
    )
    async def get_customer_orders(
        customer_id: str,
        service: OrderService = Depends(get_order_service),
    ) -> Any:
        """Retrieve all orders belonging to a customer without conflicting with /orders/{order_id}."""
        try:
            return await service.get_orders_by_customer(customer_id=customer_id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

except ImportError:
    # Standalone mock router for environments where FastAPI is not yet installed
    class MockOrderRouter:
        def __init__(self) -> None:
            self.routes = [
                ("POST", "/api/v1/orders"),
                ("GET", "/api/v1/orders/{order_id}"),
                ("GET", "/api/v1/customers/{customer_id}/orders"),
            ]

        async def create_order(self, payload: Any, service: Optional[OrderService] = None) -> Any:
            svc = service or get_order_service()
            return await svc.create_order(payload)

        async def get_order(self, order_id: str, service: Optional[OrderService] = None) -> Any:
            svc = service or get_order_service()
            return await svc.get_order(order_id=order_id)

        async def get_customer_orders(self, customer_id: str, service: Optional[OrderService] = None) -> Any:
            svc = service or get_order_service()
            return await svc.get_orders_by_customer(customer_id=customer_id)

    router = MockOrderRouter()  # type: ignore[assignment]
