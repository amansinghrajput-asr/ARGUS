"""Context hydration endpoint for n8n orchestrator."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/context", tags=["orchestration-context"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
        def patch(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.post("/hydrate")
async def hydrate_context():
    """Supply combined customer + order + case memory for n8n agent coordination (placeholder)."""
    return {
        "status": "ready",
        "customer": None,
        "recent_orders": [],
        "active_cases": [],
        "context_ready": True
    }
