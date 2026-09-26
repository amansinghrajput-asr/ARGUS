"""Pytest configuration and shared test fixtures placeholder."""

import pytest


@pytest.fixture
def sample_customer_payload() -> dict:
    """Fixture providing basic customer mock data."""
    return {
        "customer_id": "test_cust_1",
        "name": "Alex Mercer",
        "email": "alex@example.com",
        "phone": "+1-555-0100",
        "tier": "standard",
        "account_status": "active"
    }


@pytest.fixture
def sample_complaint_payload() -> dict:
    """Fixture providing basic complaint mock data."""
    return {
        "customer_id": "test_cust_1",
        "raw_complaint_text": "I ordered headphones 2 weeks ago and received the wrong item, also charged twice!",
        "order_id": "ord_9001"
    }
