"""Customer domain models and request/response validation schemas."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VALID_TIERS = {"standard", "premium", "vip"}
VALID_STATUSES = {"active", "suspended", "flagged"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_customer_fields(
    name: str,
    email: str,
    tier: str = "standard",
    account_status: str = "active",
) -> None:
    """Validate core customer field values."""
    if not name or not name.strip():
        raise ValueError("Customer 'name' must not be empty.")
    if not email or not EMAIL_REGEX.match(email.strip()):
        raise ValueError("A valid 'email' address is required.")
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier '{tier}'. Must be one of: {', '.join(sorted(VALID_TIERS))}.")
    if account_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid account_status '{account_status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}."
        )


try:
    from pydantic import BaseModel, Field, field_validator

    class CustomerCreate(BaseModel):
        """Schema for customer registration request."""

        customer_id: Optional[str] = Field(default=None, description="Optional custom unique customer identifier")
        name: str = Field(..., min_length=1, description="Customer full name")
        email: str = Field(..., description="Customer email address")
        phone: Optional[str] = Field(default=None, description="Customer phone number")
        tier: str = Field(default="standard", description="Customer loyalty tier: standard, premium, vip")
        account_status: str = Field(default="active", description="Account status: active, suspended, flagged")
        shipping_addresses: List[Dict[str, Any]] = Field(default_factory=list, description="List of shipping addresses")

        @field_validator("name")
        @classmethod
        def validate_name(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Customer 'name' must not be empty.")
            return v.strip()

        @field_validator("email")
        @classmethod
        def validate_email(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if not EMAIL_REGEX.match(v_clean):
                raise ValueError("A valid 'email' address is required.")
            return v_clean

        @field_validator("tier")
        @classmethod
        def validate_tier(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_TIERS:
                raise ValueError(f"Invalid tier '{v}'. Must be one of: {', '.join(sorted(VALID_TIERS))}.")
            return v_clean

        @field_validator("account_status")
        @classmethod
        def validate_status(cls, v: str) -> str:
            v_clean = v.strip().lower()
            if v_clean not in VALID_STATUSES:
                raise ValueError(f"Invalid account_status '{v}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}.")
            return v_clean

    class CustomerResponse(BaseModel):
        """Clean API response model for Customer entity."""

        customer_id: str
        name: str
        email: str
        phone: Optional[str] = None
        tier: str = "standard"
        account_status: str = "active"
        shipping_addresses: List[Dict[str, Any]] = Field(default_factory=list)
        created_at: str
        updated_at: str

    class CustomerBase(CustomerResponse):
        """Base customer model representation."""
        pass

except ImportError:
    class CustomerCreate:  # type: ignore[no-redef]
        """Fallback schema for customer creation when pydantic is not installed."""

        def __init__(
            self,
            name: str,
            email: str,
            customer_id: Optional[str] = None,
            phone: Optional[str] = None,
            tier: str = "standard",
            account_status: str = "active",
            shipping_addresses: Optional[List[Dict[str, Any]]] = None,
        ) -> None:
            tier_clean = (tier or "standard").strip().lower()
            status_clean = (account_status or "active").strip().lower()
            validate_customer_fields(name, email, tier_clean, status_clean)

            self.customer_id = customer_id
            self.name = name.strip()
            self.email = email.strip().lower()
            self.phone = phone.strip() if phone else None
            self.tier = tier_clean
            self.account_status = status_clean
            self.shipping_addresses = shipping_addresses or []

        def to_dict(self) -> Dict[str, Any]:
            return {
                "customer_id": self.customer_id,
                "name": self.name,
                "email": self.email,
                "phone": self.phone,
                "tier": self.tier,
                "account_status": self.account_status,
                "shipping_addresses": self.shipping_addresses,
            }

    class CustomerResponse:  # type: ignore[no-redef]
        """Fallback customer response model."""

        def __init__(
            self,
            customer_id: str,
            name: str,
            email: str,
            phone: Optional[str] = None,
            tier: str = "standard",
            account_status: str = "active",
            shipping_addresses: Optional[List[Dict[str, Any]]] = None,
            created_at: Optional[str] = None,
            updated_at: Optional[str] = None,
        ) -> None:
            self.customer_id = customer_id
            self.name = name
            self.email = email
            self.phone = phone
            self.tier = tier
            self.account_status = account_status
            self.shipping_addresses = shipping_addresses or []
            now_str = datetime.now(timezone.utc).isoformat()
            self.created_at = created_at or now_str
            self.updated_at = updated_at or now_str

        def to_dict(self) -> Dict[str, Any]:
            return {
                "customer_id": self.customer_id,
                "name": self.name,
                "email": self.email,
                "phone": self.phone,
                "tier": self.tier,
                "account_status": self.account_status,
                "shipping_addresses": self.shipping_addresses,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    class CustomerBase(CustomerResponse):  # type: ignore[no-redef]
        pass
