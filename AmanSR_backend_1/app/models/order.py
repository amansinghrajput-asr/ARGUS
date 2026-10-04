"""Order domain models and request/response validation schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

VALID_ORDER_STATUSES = {"placed", "processing", "shipped", "delivered", "cancelled", "refunded"}
VALID_PAYMENT_STATUSES = {"pending", "paid", "failed", "refunded"}


def validate_order_item_fields(
    item_id: str,
    title: str,
    quantity: int = 1,
    unit_price: float = 0.0,
) -> None:
    """Validate individual order item fields."""
    if not item_id or not str(item_id).strip():
        raise ValueError("Order item 'item_id' must not be empty.")
    if not title or not str(title).strip():
        raise ValueError("Order item 'title' must not be empty.")
    if not isinstance(quantity, int) or quantity < 1:
        raise ValueError("Order item 'quantity' must be an integer >= 1.")
    if not isinstance(unit_price, (int, float)) or unit_price < 0:
        raise ValueError("Order item 'unit_price' must be a number >= 0.0.")


def validate_order_fields(
    customer_id: str,
    status: str = "placed",
    payment_status: str = "paid",
    currency: str = "USD",
    total_amount: Optional[float] = None,
    items: Optional[List[Any]] = None,
) -> None:
    """Validate core order field values."""
    if not customer_id or not str(customer_id).strip():
        raise ValueError("Order 'customer_id' must not be empty.")
    if status not in VALID_ORDER_STATUSES:
        raise ValueError(
            f"Invalid order status '{status}'. Must be one of: {', '.join(sorted(VALID_ORDER_STATUSES))}."
        )
    if payment_status not in VALID_PAYMENT_STATUSES:
        raise ValueError(
            f"Invalid payment_status '{payment_status}'. Must be one of: {', '.join(sorted(VALID_PAYMENT_STATUSES))}."
        )
    if not currency or not str(currency).strip():
        raise ValueError("Order 'currency' must not be empty.")
    if total_amount is not None and (not isinstance(total_amount, (int, float)) or total_amount < 0):
        raise ValueError("Order 'total_amount' must be a non-negative number.")
    if items is not None:
        if not isinstance(items, list):
            raise ValueError("Order 'items' must be a list.")
        for item in items:
            if isinstance(item, dict):
                validate_order_item_fields(
                    item_id=item.get("item_id", ""),
                    title=item.get("title", ""),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price", 0.0),
                )
            elif hasattr(item, "item_id") and hasattr(item, "title"):
                validate_order_item_fields(
                    item_id=getattr(item, "item_id"),
                    title=getattr(item, "title"),
                    quantity=getattr(item, "quantity", 1),
                    unit_price=getattr(item, "unit_price", 0.0),
                )


try:
    from pydantic import BaseModel, Field, field_validator

    class OrderItem(BaseModel):
        """Schema for individual order item."""

        item_id: str = Field(..., description="Unique item identifier")
        title: str = Field(..., min_length=1, description="Item product title")
        quantity: int = Field(default=1, ge=1, description="Item quantity")
        unit_price: float = Field(default=0.0, ge=0.0, description="Unit price per item")

        @field_validator("item_id")
        @classmethod
        def validate_item_id(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Order item 'item_id' must not be empty.")
            return v.strip()

        @field_validator("title")
        @classmethod
        def validate_title(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Order item 'title' must not be empty.")
            return v.strip()

    class OrderCreate(BaseModel):
        """Schema for order creation request."""

        customer_id: str = Field(..., min_length=1, description="Associated customer ID")
        order_id: Optional[str] = Field(default=None, description="Optional custom unique order identifier")
        order_date: Optional[str] = Field(default=None, description="ISO timestamp of order placement")
        status: str = Field(default="placed", description="Order fulfillment status")
        items: List[OrderItem] = Field(default_factory=list, description="List of items in the order")
        total_amount: Optional[float] = Field(default=None, ge=0.0, description="Total order amount")
        currency: str = Field(default="USD", description="Currency ISO code")
        payment_status: str = Field(default="paid", description="Payment processing status")
        tracking_number: Optional[str] = Field(default=None, description="Shipping tracking identifier")
        carrier: Optional[str] = Field(default=None, description="Shipping carrier name")

        @field_validator("customer_id")
        @classmethod
        def validate_customer_id(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Order 'customer_id' must not be empty.")
            return v.strip()

        @field_validator("status")
        @classmethod
        def validate_status(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_ORDER_STATUSES:
                raise ValueError(
                    f"Invalid order status '{v}'. Must be one of: {', '.join(sorted(VALID_ORDER_STATUSES))}."
                )
            return v_clean

        @field_validator("payment_status")
        @classmethod
        def validate_payment_status(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_PAYMENT_STATUSES:
                raise ValueError(
                    f"Invalid payment_status '{v}'. Must be one of: {', '.join(sorted(VALID_PAYMENT_STATUSES))}."
                )
            return v_clean

        @field_validator("currency")
        @classmethod
        def validate_currency(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Order 'currency' must not be empty.")
            return v.strip().upper()

    class OrderResponse(BaseModel):
        """Clean API response model for Order entity."""

        order_id: str
        customer_id: str
        order_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        status: str = "placed"
        items: List[OrderItem] = Field(default_factory=list)
        total_amount: float = 0.0
        currency: str = "USD"
        payment_status: str = "paid"
        tracking_number: Optional[str] = None
        carrier: Optional[str] = None

    class OrderBase(OrderResponse):
        """Base order model representation."""
        pass

except ImportError:
    class OrderItem:  # type: ignore[no-redef]
        """Fallback schema for individual order item when pydantic is not installed."""

        def __init__(
            self,
            item_id: str,
            title: str,
            quantity: int = 1,
            unit_price: float = 0.0,
        ) -> None:
            validate_order_item_fields(item_id, title, quantity, unit_price)
            self.item_id = str(item_id).strip()
            self.title = str(title).strip()
            self.quantity = int(quantity)
            self.unit_price = float(unit_price)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "item_id": self.item_id,
                "title": self.title,
                "quantity": self.quantity,
                "unit_price": self.unit_price,
            }

    class OrderCreate:  # type: ignore[no-redef]
        """Fallback schema for order creation request when pydantic is not installed."""

        def __init__(
            self,
            customer_id: str,
            order_id: Optional[str] = None,
            order_date: Optional[str] = None,
            status: str = "placed",
            items: Optional[List[Any]] = None,
            total_amount: Optional[float] = None,
            currency: str = "USD",
            payment_status: str = "paid",
            tracking_number: Optional[str] = None,
            carrier: Optional[str] = None,
        ) -> None:
            status_clean = (status or "placed").strip().lower()
            payment_clean = (payment_status or "paid").strip().lower()
            currency_clean = (currency or "USD").strip().upper()
            validate_order_fields(
                customer_id=customer_id,
                status=status_clean,
                payment_status=payment_clean,
                currency=currency_clean,
                total_amount=total_amount,
                items=items,
            )

            self.customer_id = str(customer_id).strip()
            self.order_id = str(order_id).strip() if order_id else None
            self.order_date = order_date
            self.status = status_clean
            self.items = items or []
            self.total_amount = float(total_amount) if total_amount is not None else None
            self.currency = currency_clean
            self.payment_status = payment_clean
            self.tracking_number = tracking_number
            self.carrier = carrier

        def to_dict(self) -> Dict[str, Any]:
            return {
                "order_id": self.order_id,
                "customer_id": self.customer_id,
                "order_date": self.order_date,
                "status": self.status,
                "items": [i.to_dict() if hasattr(i, "to_dict") else i for i in self.items],
                "total_amount": self.total_amount,
                "currency": self.currency,
                "payment_status": self.payment_status,
                "tracking_number": self.tracking_number,
                "carrier": self.carrier,
            }

    class OrderResponse:  # type: ignore[no-redef]
        """Fallback order response model."""

        def __init__(
            self,
            order_id: str,
            customer_id: str,
            order_date: Optional[str] = None,
            status: str = "placed",
            items: Optional[List[Any]] = None,
            total_amount: float = 0.0,
            currency: str = "USD",
            payment_status: str = "paid",
            tracking_number: Optional[str] = None,
            carrier: Optional[str] = None,
        ) -> None:
            self.order_id = order_id
            self.customer_id = customer_id
            self.order_date = order_date or datetime.now(timezone.utc).isoformat()
            self.status = status
            self.items = items or []
            self.total_amount = total_amount
            self.currency = currency
            self.payment_status = payment_status
            self.tracking_number = tracking_number
            self.carrier = carrier

        def to_dict(self) -> Dict[str, Any]:
            return {
                "order_id": self.order_id,
                "customer_id": self.customer_id,
                "order_date": self.order_date,
                "status": self.status,
                "items": [i.to_dict() if hasattr(i, "to_dict") else i for i in self.items],
                "total_amount": self.total_amount,
                "currency": self.currency,
                "payment_status": self.payment_status,
                "tracking_number": self.tracking_number,
                "carrier": self.carrier,
            }

    class OrderBase(OrderResponse):  # type: ignore[no-redef]
        pass
