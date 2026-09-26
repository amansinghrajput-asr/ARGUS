"""Validation tests for Backend 1 scaffolding and modules."""

import sys
from pathlib import Path

# Add AmanSR_backend_1 root to sys.path for local discovery
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_settings_loaded():
    """Verify application configuration loads default parameters."""
    from app.core.config import settings

    assert settings.app_name == "ARGUS Backend 1"
    assert settings.mongodb_db_name == "argus_db"
    assert settings.port == 8000


def test_models_importable():
    """Verify domain models instantiate properly."""
    from app.models.customer import CustomerBase
    from app.models.order import OrderBase
    from app.models.case import ComplaintCaseBase
    from app.models.history import ConversationHistoryBase
    from app.models.knowledge import FAQArticleBase

    cust = CustomerBase(customer_id="c1", name="Test User", email="test@example.com")
    assert cust.customer_id == "c1"

    order = OrderBase(order_id="o1", customer_id="c1")
    assert order.order_id == "o1"

    case = ComplaintCaseBase(
        case_id="case_1",
        case_number="ARG-001",
        customer_id="c1",
        raw_complaint_text="Test complaint text",
    )
    assert case.case_id == "case_1"

    history = ConversationHistoryBase(history_id="h1", case_id="case_1", customer_id="c1")
    assert history.case_id == "case_1"

    faq = FAQArticleBase(
        article_id="f1",
        title="Return Policy",
        category="refunds",
        content="Policy content",
    )
    assert faq.article_id == "f1"


def test_repositories_instantiate():
    """Verify repository skeletons initialize with None DB client."""
    from app.repositories import (
        CustomerRepository,
        OrderRepository,
        CaseRepository,
        HistoryRepository,
        KnowledgeRepository,
    )

    cust_repo = CustomerRepository()
    assert cust_repo.db is None

    order_repo = OrderRepository()
    assert order_repo.db is None

    case_repo = CaseRepository()
    assert case_repo.db is None

    history_repo = HistoryRepository()
    assert history_repo.db is None

    knowledge_repo = KnowledgeRepository()
    assert knowledge_repo.db is None


def test_services_instantiate():
    """Verify service skeletons initialize properly."""
    from app.services import CaseService, HandoffService, ContextService

    assert CaseService() is not None
    assert HandoffService() is not None
    assert ContextService() is not None
