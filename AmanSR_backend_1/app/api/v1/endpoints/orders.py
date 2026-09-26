"""Order API endpoint placeholders."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/orders", tags=["orders"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.get("/{order_id}")
async def get_order(order_id: str):
    """Retrieve order details by order_id placeholder."""
    return {"order_id": order_id, "status": "placeholder"}
