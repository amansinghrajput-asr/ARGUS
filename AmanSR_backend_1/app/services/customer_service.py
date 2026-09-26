"""Customer domain business logic and service layer."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from ..core.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError
from ..models.customer import validate_customer_fields
from ..repositories.customer_repo import CustomerRepository


class CustomerService:
    """Encapsulates business rules and validation for the Customer domain."""

    def __init__(self, customer_repo: Optional[CustomerRepository] = None) -> None:
        self.customer_repo = customer_repo or CustomerRepository()

    async def create_customer(self, customer_input: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Validate, verify uniqueness, and persist a new customer."""
        data: Dict[str, Any] = (
            customer_input.to_dict()
            if hasattr(customer_input, "to_dict")
            else dict(customer_input)
            if not hasattr(customer_input, "model_dump")
            else customer_input.model_dump()
        )

        name = data.get("name", "")
        email = data.get("email", "")
        tier = data.get("tier", "standard")
        account_status = data.get("account_status", "active")
        phone = data.get("phone")
        shipping_addresses = data.get("shipping_addresses", [])

        # 1. Domain validation
        try:
            validate_customer_fields(name=name, email=email, tier=tier, account_status=account_status)
        except ValueError as e:
            raise ValidationError(str(e))

        clean_name = name.strip()
        clean_email = email.strip().lower()
        clean_phone = phone.strip() if phone else None

        # 2. Assign unique ID if not supplied
        customer_id = data.get("customer_id")
        if not customer_id or not str(customer_id).strip():
            customer_id = f"cust_{uuid.uuid4().hex[:10]}"
        else:
            customer_id = str(customer_id).strip()

        # 3. Check for ID collision
        existing_by_id = await self.customer_repo.get_by_id(customer_id)
        if existing_by_id is not None:
            raise DuplicateEntityError(f"Customer with ID '{customer_id}' already exists.")

        # 4. Check for Email uniqueness
        existing_by_email = await self.customer_repo.find_by_email(clean_email)
        if existing_by_email is not None:
            raise DuplicateEntityError(f"Customer with email '{clean_email}' already exists.")

        # 5. Build canonical customer document
        now_iso = datetime.now(timezone.utc).isoformat()
        customer_record: Dict[str, Any] = {
            "customer_id": customer_id,
            "name": clean_name,
            "email": clean_email,
            "phone": clean_phone,
            "tier": tier.strip().lower(),
            "account_status": account_status.strip().lower(),
            "shipping_addresses": shipping_addresses if isinstance(shipping_addresses, list) else [],
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # 6. Persist record
        return await self.customer_repo.create(customer_record)

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve customer by unique customer_id."""
        if not customer_id or not str(customer_id).strip():
            raise ValidationError("Invalid customer_id provided.")

        clean_id = str(customer_id).strip()
        customer = await self.customer_repo.get_by_id(clean_id)
        if customer is None:
            raise EntityNotFoundError(f"Customer with ID '{clean_id}' was not found.")
        return customer

    async def lookup_customer(self, email: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
        """Lookup customer by email or phone contact identifier."""
        clean_email = email.strip().lower() if email and str(email).strip() else None
        clean_phone = phone.strip() if phone and str(phone).strip() else None

        if not clean_email and not clean_phone:
            raise ValidationError("At least one contact identifier ('email' or 'phone') must be provided.")

        customer = await self.customer_repo.lookup(email=clean_email, phone=clean_phone)
        if customer is None:
            query_desc = f"email='{clean_email}'" if clean_email else f"phone='{clean_phone}'"
            raise EntityNotFoundError(f"No customer found matching {query_desc}.")
        return customer
