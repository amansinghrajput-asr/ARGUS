"""FAQ / Knowledge base API endpoints implementing ARGUS Knowledge domain contracts."""

from typing import Any, Dict, List, Optional

from ....core.database import get_database
from ....core.exceptions import ArgusDomainError, DuplicateEntityError, EntityNotFoundError, ValidationError
from ....models.knowledge import ArticleCreate, ArticleResponse
from ....repositories.knowledge_repo import KnowledgeRepository
from ....services.knowledge_service import KnowledgeService

# Shared service instance provider
_shared_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """Dependency provider for KnowledgeService."""
    global _shared_knowledge_service
    if _shared_knowledge_service is None:
        db = get_database()
        repo = KnowledgeRepository(db=db)
        _shared_knowledge_service = KnowledgeService(knowledge_repo=repo)
    return _shared_knowledge_service


def reset_knowledge_service(service: Optional[KnowledgeService] = None) -> None:
    """Reset shared service instance for testing isolation."""
    global _shared_knowledge_service
    _shared_knowledge_service = service


try:
    from fastapi import APIRouter, Depends, HTTPException, Query, status

    router = APIRouter(prefix="/knowledge", tags=["knowledge"])

    @router.post(
        "/articles",
        response_model=ArticleResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new FAQ article",
    )
    async def create_article(
        payload: ArticleCreate,
        service: KnowledgeService = Depends(get_knowledge_service),
    ) -> Any:
        """Create and publish a new canonical knowledge/FAQ article."""
        try:
            return await service.create_article(payload)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except DuplicateEntityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/articles",
        response_model=List[ArticleResponse],
        status_code=status.HTTP_200_OK,
        summary="List FAQ articles",
    )
    async def list_articles(
        category: Optional[str] = Query(default=None, description="Filter by category"),
        is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
        limit: int = Query(default=50, ge=1, le=100, description="Max articles to return"),
        service: KnowledgeService = Depends(get_knowledge_service),
    ) -> Any:
        """List published knowledge articles with optional category and active filters."""
        try:
            return await service.list_articles(category=category, is_active=is_active, limit=limit)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

    @router.get(
        "/articles/{id}",
        response_model=ArticleResponse,
        status_code=status.HTTP_200_OK,
        summary="Retrieve FAQ article by ID",
    )
    async def get_article(
        id: str,
        service: KnowledgeService = Depends(get_knowledge_service),
    ) -> Any:
        """Retrieve a single canonical knowledge article by ID."""
        try:
            return await service.get_article(article_id=id)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        except EntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        except ArgusDomainError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)

except ImportError:
    # Standalone mock router for environments where FastAPI is not yet installed
    class MockKnowledgeRouter:
        def __init__(self) -> None:
            self.routes = [
                ("POST", "/api/v1/knowledge/articles"),
                ("GET", "/api/v1/knowledge/articles"),
                ("GET", "/api/v1/knowledge/articles/{id}"),
            ]

        async def create_article(self, payload: Any, service: Optional[KnowledgeService] = None) -> Any:
            svc = service or get_knowledge_service()
            return await svc.create_article(payload)

        async def list_articles(
            self,
            category: Optional[str] = None,
            is_active: Optional[bool] = None,
            limit: int = 50,
            service: Optional[KnowledgeService] = None,
        ) -> Any:
            svc = service or get_knowledge_service()
            return await svc.list_articles(category=category, is_active=is_active, limit=limit)

        async def get_article(self, id: str, service: Optional[KnowledgeService] = None) -> Any:
            svc = service or get_knowledge_service()
            return await svc.get_article(article_id=id)

    router = MockKnowledgeRouter()  # type: ignore[assignment]
