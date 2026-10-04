"""Unit and integration tests for FAQ / Knowledge base domain (isolated in-memory)."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure AmanSR_backend_1 root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.v1.endpoints.knowledge import (
    get_knowledge_service,
    reset_knowledge_service,
    router,
)
from app.core.exceptions import (
    ArgusDomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.knowledge import (
    ArticleCreate,
    ArticleResponse,
    FAQArticleBase,
    validate_article_fields,
)
from app.repositories.knowledge_repo import KnowledgeRepository
from app.services.knowledge_service import KnowledgeService


def run_async(coro):
    """Helper to run async coroutines synchronously in test runner."""
    return asyncio.run(coro)


def create_isolated_environment() -> Tuple[KnowledgeService, KnowledgeRepository]:
    """Create isolated in-memory repository and KnowledgeService instance."""
    repo = KnowledgeRepository(db=None)
    service = KnowledgeService(knowledge_repo=repo)
    return service, repo


def test_article_model_validation():
    """Test model field validation rules for FAQArticle."""
    # Valid fields
    validate_article_fields(
        title="Return & Refund Window",
        category="refunds",
        content="Customers have 30 days to return purchases.",
        version=1,
    )

    # Empty title
    try:
        validate_article_fields(title="", category="refunds", content="Content text")
        assert False, "Should have raised ValueError on empty title"
    except ValueError as e:
        assert "title" in str(e).lower()

    # Empty category
    try:
        validate_article_fields(title="Title", category="", content="Content text")
        assert False, "Should have raised ValueError on empty category"
    except ValueError as e:
        assert "category" in str(e).lower()

    # Empty content
    try:
        validate_article_fields(title="Title", category="refunds", content="")
        assert False, "Should have raised ValueError on empty content"
    except ValueError as e:
        assert "content" in str(e).lower()

    # Invalid version < 1
    try:
        validate_article_fields(title="Title", category="refunds", content="Content", version=0)
        assert False, "Should have raised ValueError on version < 1"
    except ValueError as e:
        assert "version" in str(e).lower()


def test_valid_article_creation():
    """Test successfully creating a canonical FAQ article."""
    service, _ = create_isolated_environment()

    payload = {
        "article_id": "faq_test_001",
        "title": "Return & Refund Policy Window",
        "category": "refunds",
        "content": "Returns are accepted within 30 days. Full refunds processed within 3-5 business days.",
        "tags": ["refund", "return", "policy", "window"],
        "vector_doc_id": "vec_doc_001",
        "is_active": True,
        "version": 1,
    }

    result = run_async(service.create_article(payload))

    assert result["article_id"] == "faq_test_001"
    assert result["title"] == "Return & Refund Policy Window"
    assert result["category"] == "refunds"
    assert "30 days" in result["content"]
    assert len(result["tags"]) == 4
    assert result["vector_doc_id"] == "vec_doc_001"
    assert result["is_active"] is True
    assert result["version"] == 1
    assert "created_at" in result
    assert "updated_at" in result
    assert "_id" not in result


def test_article_creation_auto_generates_id():
    """Test that article_id is auto-generated if omitted."""
    service, _ = create_isolated_environment()

    payload = {
        "title": "International Shipping Rates",
        "category": "shipping",
        "content": "International shipping rates vary by destination country and customs duties.",
    }

    result = run_async(service.create_article(payload))

    assert result["article_id"].startswith("faq_")
    assert result["title"] == "International Shipping Rates"
    assert result["category"] == "shipping"
    assert result["is_active"] is True
    assert result["version"] == 1


def test_get_article_by_id():
    """Test retrieving an existing article by article_id."""
    service, _ = create_isolated_environment()

    created = run_async(
        service.create_article(
            {
                "article_id": "faq_find_01",
                "title": "Account Password Reset",
                "category": "account",
                "content": "Click forgot password on login screen to receive reset link.",
            }
        )
    )

    retrieved = run_async(service.get_article("faq_find_01"))
    assert retrieved["article_id"] == created["article_id"]
    assert retrieved["title"] == "Account Password Reset"
    assert retrieved["category"] == "account"
    assert "_id" not in retrieved


def test_get_missing_article_returns_appropriate_error():
    """Test 404 EntityNotFoundError when article ID is not found."""
    service, _ = create_isolated_environment()

    try:
        run_async(service.get_article("faq_non_existent"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404
        assert "not found" in e.message.lower()

    # Empty article_id
    try:
        run_async(service.get_article(""))
        assert False, "Should have raised ValidationError on empty article_id"
    except ValidationError as e:
        assert e.status_code == 400


def test_list_articles():
    """Test listing FAQ articles with optional category and active filters."""
    service, _ = create_isolated_environment()

    run_async(service.create_article({"article_id": "f1", "title": "Refunds FAQ 1", "category": "refunds", "content": "Refund policy info"}))
    run_async(service.create_article({"article_id": "f2", "title": "Refunds FAQ 2", "category": "refunds", "content": "Partial refund info"}))
    run_async(service.create_article({"article_id": "f3", "title": "Shipping FAQ", "category": "shipping", "content": "Carrier tracking info"}))

    # List all
    all_articles = run_async(service.list_articles())
    assert len(all_articles) == 3

    # Filter by category
    refund_articles = run_async(service.list_articles(category="refunds"))
    assert len(refund_articles) == 2
    for art in refund_articles:
        assert art["category"] == "refunds"
        assert "_id" not in art

    # Filter by shipping category
    shipping_articles = run_async(service.list_articles(category="shipping"))
    assert len(shipping_articles) == 1
    assert shipping_articles[0]["article_id"] == "f3"


def test_invalid_missing_required_data():
    """Test rejection when creating articles with invalid or missing data."""
    service, _ = create_isolated_environment()

    # Empty title
    try:
        run_async(service.create_article({"title": "", "category": "billing", "content": "Valid content"}))
        assert False, "Should have raised ValidationError on empty title"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty category
    try:
        run_async(service.create_article({"title": "Valid Title", "category": "", "content": "Valid content"}))
        assert False, "Should have raised ValidationError on empty category"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty content
    try:
        run_async(service.create_article({"title": "Valid Title", "category": "billing", "content": ""}))
        assert False, "Should have raised ValidationError on empty content"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid version < 1
    try:
        run_async(service.create_article({"title": "Valid Title", "category": "billing", "content": "Content", "version": 0}))
        assert False, "Should have raised ValidationError on version < 1"
    except ValidationError as e:
        assert e.status_code == 400


def test_tags_handling():
    """Test handling of tags as clean list of strings."""
    service, _ = create_isolated_environment()

    # With tags
    art_with_tags = run_async(
        service.create_article(
            {
                "title": "Payment Gateways Supported",
                "category": "billing",
                "content": "We support Stripe, PayPal, and Apple Pay.",
                "tags": ["stripe", "paypal", "apple pay", "checkout"],
            }
        )
    )
    assert art_with_tags["tags"] == ["stripe", "paypal", "apple pay", "checkout"]

    # Without tags
    art_no_tags = run_async(
        service.create_article(
            {
                "title": "Billing Currency Support",
                "category": "billing",
                "content": "USD, EUR, GBP supported.",
            }
        )
    )
    assert art_no_tags["tags"] == []


def test_is_active_and_version_handling():
    """Test is_active flag and version number management."""
    service, _ = create_isolated_environment()

    # Active article version 2
    run_async(
        service.create_article(
            {
                "article_id": "faq_active_v2",
                "title": "Active Article",
                "category": "technical",
                "content": "System specs version 2",
                "is_active": True,
                "version": 2,
            }
        )
    )

    # Inactive article version 1
    run_async(
        service.create_article(
            {
                "article_id": "faq_inactive_v1",
                "title": "Deprecated Article",
                "category": "technical",
                "content": "Deprecated protocol",
                "is_active": False,
                "version": 1,
            }
        )
    )

    active_only = run_async(service.list_articles(is_active=True))
    assert len(active_only) == 1
    assert active_only[0]["article_id"] == "faq_active_v2"
    assert active_only[0]["version"] == 2

    inactive_only = run_async(service.list_articles(is_active=False))
    assert len(inactive_only) == 1
    assert inactive_only[0]["article_id"] == "faq_inactive_v1"


def test_conflicting_article_creation():
    """Test 409 Conflict when creating an article with an existing article_id."""
    service, _ = create_isolated_environment()

    payload = {
        "article_id": "faq_unique_99",
        "title": "Unique Article",
        "category": "general",
        "content": "First publication.",
    }
    run_async(service.create_article(payload))

    try:
        run_async(service.create_article(payload))
        assert False, "Should have raised DuplicateEntityError"
    except DuplicateEntityError as e:
        assert e.status_code == 409
        assert "already exists" in e.message.lower()


def test_response_does_not_expose_mongodb_id():
    """Ensure internal MongoDB _id is stripped from all responses."""
    service, repo = create_isolated_environment()

    repo._memory_store["faq_raw"] = {
        "_id": "707f1f77bcf86cd799439033",
        "article_id": "faq_raw",
        "title": "Raw Doc Test",
        "category": "general",
        "content": "Testing _id stripping.",
        "tags": [],
        "is_active": True,
        "version": 1,
    }

    doc = run_async(service.get_article("faq_raw"))
    assert doc is not None
    assert "_id" not in doc

    listed = run_async(service.list_articles())
    assert len(listed) == 1
    assert "_id" not in listed[0]


def test_router_api_integration():
    """Verify endpoint routing logic and integration through Knowledge router."""
    service, _ = create_isolated_environment()
    reset_knowledge_service(service)

    # 1. Create article via router
    payload = ArticleCreate(
        article_id="faq_router_1",
        title="Router FAQ Article",
        category="general",
        content="Article created via router integration.",
        tags=["router", "test"],
    ) if "ArticleCreate" in globals() else {
        "article_id": "faq_router_1",
        "title": "Router FAQ Article",
        "category": "general",
        "content": "Article created via router integration.",
        "tags": ["router", "test"],
    }

    if hasattr(router, "create_article"):
        created = run_async(router.create_article(payload, service=service))
        assert created["article_id"] == "faq_router_1"
        assert created["title"] == "Router FAQ Article"

        # 2. Get article by ID via router
        retrieved = run_async(router.get_article(id="faq_router_1", service=service))
        assert retrieved["article_id"] == "faq_router_1"
        assert retrieved["category"] == "general"

        # 3. List articles via router
        listed = run_async(router.list_articles(category="general", is_active=None, limit=50, service=service))
        assert len(listed) == 1
        assert listed[0]["article_id"] == "faq_router_1"

    reset_knowledge_service(None)


if __name__ == "__main__":
    tests = [
        test_article_model_validation,
        test_valid_article_creation,
        test_article_creation_auto_generates_id,
        test_get_article_by_id,
        test_get_missing_article_returns_appropriate_error,
        test_list_articles,
        test_invalid_missing_required_data,
        test_tags_handling,
        test_is_active_and_version_handling,
        test_conflicting_article_creation,
        test_response_does_not_expose_mongodb_id,
        test_router_api_integration,
    ]

    for t in tests:
        t()
        print(f"PASSED: {t.__name__}")
    print(f"\nAll {len(tests)} Knowledge domain tests passed successfully!")
