"""Order domain model schema placeholder."""

from typing import List, Optional
from datetime import datetime

try:
    from pydantic import BaseModel, Field

    class OrderItem(BaseModel):
        """Minimal schema for an item inside an order."""

        item_id: str
        title: str
        quantity: int
        unit_price: float

    class OrderBase(BaseModel):
        """Minimal schema for Order entity."""

        order_id: str
        customer_id: str
        order_date: Optional[datetime] = None
        status: str = "placed"  # placed, processing, shipped, delivered, cancelled, refunded
        total_amount: float = 0.0
        currency: str = "USD"
        payment_status: str = "paid"  # paid, pending, failed, refunded
        items: List[OrderItem] = Field(default_factory=list)

except ImportError:
    class OrderItem:  # type: ignore[no-redef]
        def __init__(self, item_id: str, title: str, quantity: int, unit_price: float) -> None:
            self.item_id = item_id
            self.title = title
            self.quantity = quantity
            self.unit_price = unit_price

    class OrderBase:  # type: ignore[no-redef]
        def __init__(
            self,
            order_id: str,
            customer_id: str,
            status: str = "placed",
            total_amount: float = 0.0,
            currency: str = "USD",
        ) -> None:
            self.order_id = order_id
            self.customer_id = customer_id
            self.status = status
            self.total_amount = total_amount
            self.currency = currency
            self.items: List[OrderItem] = []
