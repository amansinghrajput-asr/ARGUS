"""Customer API endpoint placeholders."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/customers", tags=["customers"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
        def patch(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.get("/")
async def list_customers():
    """List customer records placeholder."""
    return {"message": "Customer listing placeholder"}


@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    """Get single customer profile placeholder."""
    return {"customer_id": customer_id, "status": "placeholder"}
