"""FAQ / Knowledge base endpoint placeholders."""

try:
    from fastapi import APIRouter
    router = APIRouter(prefix="/knowledge", tags=["knowledge"])
except ImportError:
    class MockRouter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
        def patch(self, *args, **kwargs): return lambda f: f
    router = MockRouter()


@router.get("/articles")
async def list_articles():
    """List FAQ knowledge articles placeholder."""
    return {"articles": []}


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Retrieve single knowledge article placeholder."""
    return {"article_id": article_id, "status": "placeholder"}
