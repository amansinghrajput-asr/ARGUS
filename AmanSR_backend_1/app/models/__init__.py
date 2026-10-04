"""Data schemas and domain models for Backend 1."""

from .customer import CustomerBase, CustomerCreate, CustomerResponse
from .order import OrderBase, OrderCreate, OrderItem, OrderResponse
from .case import CaseCreate, CaseResponse, CaseUpdate, ComplaintCaseBase
from .history import ConversationHistoryBase
from .knowledge import FAQArticleBase

__all__ = [
    "CustomerBase",
    "CustomerCreate",
    "CustomerResponse",
    "OrderBase",
    "OrderItem",
    "OrderCreate",
    "OrderResponse",
    "ComplaintCaseBase",
    "CaseCreate",
    "CaseUpdate",
    "CaseResponse",
    "ConversationHistoryBase",
    "FAQArticleBase",
]
