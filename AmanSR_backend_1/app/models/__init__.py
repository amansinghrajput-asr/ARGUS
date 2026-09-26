"""Data schemas and domain models for Backend 1."""

from .customer import CustomerBase
from .order import OrderBase
from .case import ComplaintCaseBase
from .history import ConversationHistoryBase
from .knowledge import FAQArticleBase

__all__ = [
    "CustomerBase",
    "OrderBase",
    "ComplaintCaseBase",
    "ConversationHistoryBase",
    "FAQArticleBase",
]
