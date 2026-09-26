"""Customer domain model schema placeholder."""

from typing import List, Optional
from datetime import datetime

try:
    from pydantic import BaseModel, Field

    class CustomerBase(BaseModel):
        """Minimal schema for Customer entity."""

        customer_id: str
        name: str
        email: str
        phone: Optional[str] = None
        tier: str = "standard"  # standard, premium, vip
        account_status: str = "active"  # active, suspended, flagged
        created_at: Optional[datetime] = None

except ImportError:
    class CustomerBase:  # type: ignore[no-redef]
        """Placeholder for Customer entity when pydantic is not installed."""

        def __init__(
            self,
            customer_id: str,
            name: str,
            email: str,
            phone: Optional[str] = None,
            tier: str = "standard",
            account_status: str = "active",
        ) -> None:
            self.customer_id = customer_id
            self.name = name
            self.email = email
            self.phone = phone
            self.tier = tier
            self.account_status = account_status
