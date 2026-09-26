"""Aggregator router for V1 endpoints."""

from .endpoints.customers import router as customers_router
from .endpoints.orders import router as orders_router
from .endpoints.cases import router as cases_router
from .endpoints.history import router as history_router
from .endpoints.knowledge import router as knowledge_router
from .endpoints.context import router as context_router

try:
    from fastapi import APIRouter
    v1_router = APIRouter()
    v1_router.include_router(customers_router)
    v1_router.include_router(orders_router)
    v1_router.include_router(cases_router)
    v1_router.include_router(history_router)
    v1_router.include_router(knowledge_router)
    v1_router.include_router(context_router)
except ImportError:
    class MockV1Router:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.sub_routers = [
                customers_router,
                orders_router,
                cases_router,
                history_router,
                knowledge_router,
                context_router,
            ]
    v1_router = MockV1Router()
