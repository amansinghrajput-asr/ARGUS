"""Top-level API router aggregator."""

from .v1.router import v1_router

try:
    from fastapi import APIRouter
    api_router = APIRouter(prefix="/api")
    api_router.include_router(v1_router, prefix="/v1")
except ImportError:
    class MockApiRouter:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.v1 = v1_router
    api_router = MockApiRouter()
