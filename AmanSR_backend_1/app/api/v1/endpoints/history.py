"""Conversation history and zero-repeat handoff endpoint placeholders."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/cases", tags=["history"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
        def patch(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.get("/{case_id}/history")
async def get_case_history(case_id: str):
    """Retrieve full conversation memory and specialist trails placeholder."""
    return {"case_id": case_id, "messages": [], "investigation_trail": []}


@router.get("/{case_id}/handoff")
async def get_human_handoff_packet(case_id: str):
    """Retrieve structured zero-repeat handoff packet for human agent placeholder."""
    return {
        "case_id": case_id,
        "handoff_summary": "Zero-repeat context snapshot placeholder",
        "status": "escalated_to_human"
    }
