"""Order domain business logic and service layer."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ..core.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError
from ..models.order import validate_order_fields, validate_order_item_fields
from ..repositories.customer_repo import CustomerRepository
from ..repositories.order_repo import OrderRepository


class OrderService:
    """Encapsulates business rules and validation for the Order domain."""

    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
    ) -> None:
        self.order_repo = order_repo or OrderRepository()
        self.customer_repo = customer_repo

    async def create_order(self, order_input: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Validate, verify references, and persist a new order."""
        data: Dict[str, Any] = (
            order_input.to_dict()
            if hasattr(order_input, "to_dict")
            else dict(order_input)
            if not hasattr(order_input, "model_dump")
            else order_input.model_dump()
        )

        customer_id = data.get("customer_id", "")
        status = data.get("status", "placed")
        payment_status = data.get("payment_status", "paid")
        currency = data.get("currency", "USD")
        total_amount = data.get("total_amount")
        items = data.get("items", [])
        tracking_number = data.get("tracking_number")
        carrier = data.get("carrier")
        order_date = data.get("order_date")

        # 1. Domain schema validation
        try:
            validate_order_fields(
                customer_id=customer_id,
                status=status,
                payment_status=payment_status,
                currency=currency,
                total_amount=total_amount,
                items=items,
            )
        except ValueError as e:
            raise ValidationError(str(e))

        clean_customer_id = str(customer_id).strip()
        clean_currency = str(currency).strip().upper()
        clean_status = str(status).strip().lower()
        clean_payment = str(payment_status).strip().lower()

        # 2. Referenced customer existence check (if customer_repo is available)
        if self.customer_repo is not None:
            customer = await self.customer_repo.get_by_id(clean_customer_id)
            if customer is None:
                raise EntityNotFoundError(f"Customer with ID '{clean_customer_id}' was not found.")

        # 3. Assign or validate unique order_id
        order_id = data.get("order_id")
        if not order_id or not str(order_id).strip():
            order_id = f"ord_{uuid.uuid4().hex[:10]}"
        else:
            order_id = str(order_id).strip()

        # 4. Check for Order ID collision
        existing_order = await self.order_repo.get_by_id(order_id)
        if existing_order is not None:
            raise DuplicateEntityError(f"Order with ID '{order_id}' already exists.")

        # 5. Sanitize items and compute total if not explicitly provided
        sanitized_items: List[Dict[str, Any]] = []
        computed_total = 0.0

        for item in items:
            i_dict: Dict[str, Any] = (
                item.to_dict()
                if hasattr(item, "to_dict")
                else dict(item)
                if not hasattr(item, "model_dump")
                else item.model_dump()
            )
            try:
                validate_order_item_fields(
                    item_id=i_dict.get("item_id", ""),
                    title=i_dict.get("title", ""),
                    quantity=i_dict.get("quantity", 1),
                    unit_price=i_dict.get("unit_price", 0.0),
                )
            except ValueError as e:
                raise ValidationError(str(e))

            qty = int(i_dict.get("quantity", 1))
            price = float(i_dict.get("unit_price", 0.0))
            computed_total += qty * price
            sanitized_items.append(
                {
                    "item_id": str(i_dict["item_id"]).strip(),
                    "title": str(i_dict["title"]).strip(),
                    "quantity": qty,
                    "unit_price": price,
                }
            )

        final_total = round(float(total_amount), 2) if total_amount is not None else round(computed_total, 2)

        # 6. Build canonical order document
        now_iso = str(order_date).strip() if order_date and str(order_date).strip() else datetime.now(timezone.utc).isoformat()
        order_record: Dict[str, Any] = {
            "order_id": order_id,
            "customer_id": clean_customer_id,
            "order_date": now_iso,
            "status": clean_status,
            "items": sanitized_items,
            "total_amount": final_total,
            "currency": clean_currency,
            "payment_status": clean_payment,
            "tracking_number": str(tracking_number).strip() if tracking_number else None,
            "carrier": str(carrier).strip() if carrier else None,
        }

        # 7. Persist record
        return await self.order_repo.create(order_record)

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Retrieve order by unique order_id."""
        if not order_id or not str(order_id).strip():
            raise ValidationError("Invalid order_id provided.")

        clean_id = str(order_id).strip()
        order = await self.order_repo.get_by_id(clean_id)
        if order is None:
            raise EntityNotFoundError(f"Order with ID '{clean_id}' was not found.")
        return order

    async def get_orders_by_customer(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve all orders associated with a customer_id."""
        if not customer_id or not str(customer_id).strip():
            raise ValidationError("Invalid customer_id provided.")

        clean_id = str(customer_id).strip()

        # Verify referenced customer exists if customer repository is attached
        if self.customer_repo is not None:
            customer = await self.customer_repo.get_by_id(clean_id)
            if customer is None:
                raise EntityNotFoundError(f"Customer with ID '{clean_id}' was not found.")

        return await self.order_repo.get_by_customer_id(clean_id, limit=limit)
