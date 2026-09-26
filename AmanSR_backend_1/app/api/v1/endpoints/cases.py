"""Complaint and Case lifecycle API endpoint placeholders."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/cases", tags=["cases"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
        def patch(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.post("/")
async def create_case():
    """Ingest new complaint case placeholder."""
    return {"status": "created", "case_id": "placeholder_case"}


@router.get("/{case_id}")
async def get_case(case_id: str):
    """Retrieve case details and triage status placeholder."""
    return {"case_id": case_id, "status": "placeholder"}
