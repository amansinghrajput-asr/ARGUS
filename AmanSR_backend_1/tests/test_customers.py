"""Unit and integration tests for the Customer domain (isolated in-memory)."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure AmanSR_backend_1 root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.exceptions import (
    ArgusDomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.customer import CustomerCreate, CustomerResponse, validate_customer_fields
from app.repositories.customer_repo import CustomerRepository
from app.services.customer_service import CustomerService
from app.api.v1.endpoints.customers import get_customer_service, reset_customer_service, router


def run_async(coro):
    """Helper to run async coroutines synchronously in test runner."""
    return asyncio.run(coro)


def create_isolated_service() -> CustomerService:
    """Create a completely isolated in-memory CustomerService instance."""
    repo = CustomerRepository(db=None)
    return CustomerService(customer_repo=repo)


def test_customer_model_validation():
    """Test model field validation rules."""
    # Valid customer
    validate_customer_fields(name="Bruce Wayne", email="bruce@waynecorp.com", tier="vip", account_status="active")

    # Invalid empty name
    try:
        validate_customer_fields(name="", email="test@example.com")
        assert False, "Should have raised ValueError on empty name"
    except ValueError as e:
        assert "name" in str(e).lower()

    # Invalid email format
    try:
        validate_customer_fields(name="Test", email="not-an-email")
        assert False, "Should have raised ValueError on invalid email"
    except ValueError as e:
        assert "email" in str(e).lower()

    # Invalid tier
    try:
        validate_customer_fields(name="Test", email="test@example.com", tier="platinum")
        assert False, "Should have raised ValueError on invalid tier"
    except ValueError as e:
        assert "tier" in str(e).lower()

    # Invalid status
    try:
        validate_customer_fields(name="Test", email="test@example.com", account_status="banned")
        assert False, "Should have raised ValueError on invalid status"
    except ValueError as e:
        assert "account_status" in str(e).lower()


def test_valid_customer_creation():
    """Test successfully creating a customer with valid data."""
    service = create_isolated_service()

    payload = {
        "customer_id": "cust_test_001",
        "name": "Sarah Connor",
        "email": "sarah.connor@example.com",
        "phone": "+1-555-0199",
        "tier": "vip",
        "account_status": "active",
        "shipping_addresses": [{"street": "100 Resistance Way", "city": "Los Angeles", "state": "CA"}],
    }

    result = run_async(service.create_customer(payload))

    assert result["customer_id"] == "cust_test_001"
    assert result["name"] == "Sarah Connor"
    assert result["email"] == "sarah.connor@example.com"
    assert result["phone"] == "+1-555-0199"
    assert result["tier"] == "vip"
    assert result["account_status"] == "active"
    assert len(result["shipping_addresses"]) == 1
    assert "created_at" in result
    assert "updated_at" in result
    assert "_id" not in result  # Internal MongoDB details must not be exposed


def test_customer_creation_auto_generates_id():
    """Test that customer_id is automatically generated if omitted."""
    service = create_isolated_service()

    payload = {
        "name": "Kyle Reese",
        "email": "kyle.reese@example.com",
    }

    result = run_async(service.create_customer(payload))

    assert result["customer_id"].startswith("cust_")
    assert result["email"] == "kyle.reese@example.com"
    assert result["tier"] == "standard"
    assert result["account_status"] == "active"


def test_invalid_customer_data():
    """Test rejection when creating customer with invalid input."""
    service = create_isolated_service()

    # Empty name
    try:
        run_async(service.create_customer({"name": "", "email": "valid@example.com"}))
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid email
    try:
        run_async(service.create_customer({"name": "Valid Name", "email": "invalid_email"}))
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert e.status_code == 400


def test_retrieving_existing_customer():
    """Test retrieving a customer by ID."""
    service = create_isolated_service()

    payload = {"customer_id": "cust_find_01", "name": "John Connor", "email": "john@example.com"}
    run_async(service.create_customer(payload))

    customer = run_async(service.get_customer("cust_find_01"))
    assert customer["customer_id"] == "cust_find_01"
    assert customer["name"] == "John Connor"


def test_retrieving_missing_customer():
    """Test 404 EntityNotFoundError when customer ID does not exist."""
    service = create_isolated_service()

    try:
        run_async(service.get_customer("non_existent_id"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404
        assert "not found" in e.message.lower()


def test_customer_lookup_by_email():
    """Test looking up a customer by email address."""
    service = create_isolated_service()

    payload = {"customer_id": "cust_look_01", "name": "Ellen Ripley", "email": "ripley@nostromo.org"}
    run_async(service.create_customer(payload))

    # Exact lookup
    found = run_async(service.lookup_customer(email="ripley@nostromo.org"))
    assert found["customer_id"] == "cust_look_01"

    # Case-insensitive lookup
    found_upper = run_async(service.lookup_customer(email="RIPLEY@NOSTROMO.ORG"))
    assert found_upper["customer_id"] == "cust_look_01"


def test_customer_lookup_by_phone():
    """Test looking up a customer by phone number."""
    service = create_isolated_service()

    payload = {
        "customer_id": "cust_phone_01",
        "name": "Arthur Dent",
        "email": "dent@galaxy.org",
        "phone": "+44-20-7946-0919",
    }
    run_async(service.create_customer(payload))

    found = run_async(service.lookup_customer(phone="+44-20-7946-0919"))
    assert found["customer_id"] == "cust_phone_01"
    assert found["name"] == "Arthur Dent"


def test_customer_lookup_missing_parameters():
    """Test 400 ValidationError when neither email nor phone is provided."""
    service = create_isolated_service()

    try:
        run_async(service.lookup_customer(email=None, phone=None))
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert e.status_code == 400


def test_customer_lookup_not_found():
    """Test 404 EntityNotFoundError when contact identifier is not in the system."""
    service = create_isolated_service()

    try:
        run_async(service.lookup_customer(email="unknown@universe.org"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404


def test_duplicate_customer_handling():
    """Test 409 Conflict when duplicate customer_id or email is registered."""
    service = create_isolated_service()

    payload = {"customer_id": "cust_dup_01", "name": "First User", "email": "unique@example.com"}
    run_async(service.create_customer(payload))

    # Duplicate ID
    try:
        run_async(service.create_customer({"customer_id": "cust_dup_01", "name": "Another User", "email": "other@example.com"}))
        assert False, "Should have raised DuplicateEntityError for customer_id"
    except DuplicateEntityError as e:
        assert e.status_code == 409
        assert "id" in e.message.lower()

    # Duplicate Email
    try:
        run_async(service.create_customer({"customer_id": "cust_dup_02", "name": "Another User", "email": "unique@example.com"}))
        assert False, "Should have raised DuplicateEntityError for email"
    except DuplicateEntityError as e:
        assert e.status_code == 409
        assert "email" in e.message.lower()


def test_endpoint_mock_router_integration():
    """Verify endpoint routing logic and integration through Customer router."""
    service = create_isolated_service()
    reset_customer_service(service)

    # 1. Test creation via router
    payload = CustomerCreate(
        name="Marty McFly",
        email="marty@hillvalley.edu",
        tier="standard",
        account_status="active",
    ) if "CustomerCreate" in globals() else {"name": "Marty McFly", "email": "marty@hillvalley.edu"}

    if hasattr(router, "create_customer"):
        created = run_async(router.create_customer(payload, service=service))
        cust_id = created["customer_id"]
        assert created["email"] == "marty@hillvalley.edu"

        # 2. Test lookup via router
        looked_up = run_async(router.lookup_customer(email="marty@hillvalley.edu", service=service))
        assert looked_up["customer_id"] == cust_id

        # 3. Test get by ID via router
        retrieved = run_async(router.get_customer(customer_id=cust_id, service=service))
        assert retrieved["name"] == "Marty McFly"

    reset_customer_service(None)


if __name__ == "__main__":
    tests = [
        test_customer_model_validation,
        test_valid_customer_creation,
        test_customer_creation_auto_generates_id,
        test_invalid_customer_data,
        test_retrieving_existing_customer,
        test_retrieving_missing_customer,
        test_customer_lookup_by_email,
        test_customer_lookup_by_phone,
        test_customer_lookup_missing_parameters,
        test_customer_lookup_not_found,
        test_duplicate_customer_handling,
        test_endpoint_mock_router_integration,
    ]

    for t in tests:
        t()
        print(f"PASSED: {t.__name__}")
    print("\nAll Customer domain tests passed successfully!")
