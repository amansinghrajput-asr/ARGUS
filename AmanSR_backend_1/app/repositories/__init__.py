"""Repository access layer for MongoDB collections."""

from .customer_repo import CustomerRepository
from .order_repo import OrderRepository
from .case_repo import CaseRepository
from .history_repo import HistoryRepository
from .knowledge_repo import KnowledgeRepository

__all__ = [
    "CustomerRepository",
    "OrderRepository",
    "CaseRepository",
    "HistoryRepository",
    "KnowledgeRepository",
]
