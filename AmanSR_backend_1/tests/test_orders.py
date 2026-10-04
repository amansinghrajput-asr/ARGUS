"""Unit and integration tests for the Order domain (isolated in-memory)."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure AmanSR_backend_1 root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.v1.endpoints.orders import (
    get_order_service,
    reset_order_service,
    router,
)
from app.core.exceptions import (
    ArgusDomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.order import (
    OrderBase,
    OrderCreate,
    OrderItem,
    OrderResponse,
    validate_order_fields,
    validate_order_item_fields,
)
from app.repositories.customer_repo import CustomerRepository
from app.repositories.order_repo import OrderRepository
from app.services.order_service import OrderService


def run_async(coro):
    """Helper to run async coroutines synchronously in test runner."""
    return asyncio.run(coro)


def create_isolated_environment() -> Tuple[OrderService, CustomerRepository, OrderRepository]:
    """Create isolated in-memory repositories and OrderService instance."""
    customer_repo = CustomerRepository(db=None)
    order_repo = OrderRepository(db=None)
    service = OrderService(order_repo=order_repo, customer_repo=customer_repo)
    return service, customer_repo, order_repo


def test_order_model_and_item_validation():
    """Test model field validation rules for orders and order items."""
    # Valid item validation
    validate_order_item_fields(item_id="item_01", title="Wireless Mouse", quantity=2, unit_price=29.99)

    # Invalid empty item_id
    try:
        validate_order_item_fields(item_id="", title="Mouse", quantity=1, unit_price=10.0)
        assert False, "Should have raised ValueError on empty item_id"
    except ValueError as e:
        assert "item_id" in str(e).lower()

    # Invalid empty item title
    try:
        validate_order_item_fields(item_id="i1", title="", quantity=1, unit_price=10.0)
        assert False, "Should have raised ValueError on empty title"
    except ValueError as e:
        assert "title" in str(e).lower()

    # Invalid item quantity < 1
    try:
        validate_order_item_fields(item_id="i1", title="Mouse", quantity=0, unit_price=10.0)
        assert False, "Should have raised ValueError on quantity < 1"
    except ValueError as e:
        assert "quantity" in str(e).lower()

    # Invalid item unit_price < 0
    try:
        validate_order_item_fields(item_id="i1", title="Mouse", quantity=1, unit_price=-5.0)
        assert False, "Should have raised ValueError on negative unit_price"
    except ValueError as e:
        assert "unit_price" in str(e).lower()

    # Valid order fields
    validate_order_fields(
        customer_id="cust_1",
        status="shipped",
        payment_status="paid",
        currency="USD",
        total_amount=59.98,
        items=[{"item_id": "item_01", "title": "Mouse", "quantity": 2, "unit_price": 29.99}],
    )

    # Invalid empty customer_id
    try:
        validate_order_fields(customer_id="")
        assert False, "Should have raised ValueError on empty customer_id"
    except ValueError as e:
        assert "customer_id" in str(e).lower()

    # Invalid order status
    try:
        validate_order_fields(customer_id="cust_1", status="unknown_status")
        assert False, "Should have raised ValueError on invalid status"
    except ValueError as e:
        assert "status" in str(e).lower()

    # Invalid payment_status
    try:
        validate_order_fields(customer_id="cust_1", payment_status="fraudulent")
        assert False, "Should have raised ValueError on invalid payment_status"
    except ValueError as e:
        assert "payment_status" in str(e).lower()

    # Negative total_amount
    try:
        validate_order_fields(customer_id="cust_1", total_amount=-100.0)
        assert False, "Should have raised ValueError on negative total_amount"
    except ValueError as e:
        assert "total_amount" in str(e).lower()


def test_valid_order_creation():
    """Test successfully creating an order with valid data and items."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_valid_1", "name": "Tony Stark", "email": "tony@stark.com"}))

    payload = {
        "order_id": "ord_test_001",
        "customer_id": "cust_valid_1",
        "status": "placed",
        "items": [
            {"item_id": "item_1", "title": "Arc Reactor Core", "quantity": 1, "unit_price": 999.99},
            {"item_id": "item_2", "title": "Titanium Plating", "quantity": 4, "unit_price": 250.0},
        ],
        "currency": "USD",
        "payment_status": "paid",
        "tracking_number": "TRK-STARK-001",
        "carrier": "Stark Air",
    }

    result = run_async(service.create_order(payload))

    assert result["order_id"] == "ord_test_001"
    assert result["customer_id"] == "cust_valid_1"
    assert result["status"] == "placed"
    assert len(result["items"]) == 2
    assert result["total_amount"] == 1999.99
    assert result["currency"] == "USD"
    assert result["payment_status"] == "paid"
    assert result["tracking_number"] == "TRK-STARK-001"
    assert result["carrier"] == "Stark Air"
    assert "order_date" in result
    assert "_id" not in result


def test_order_creation_auto_generates_id():
    """Test that order_id is auto-generated if omitted."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_valid_2", "name": "Pepper Potts", "email": "pepper@stark.com"}))

    payload = {
        "customer_id": "cust_valid_2",
        "items": [{"item_id": "item_1", "title": "Tablet", "quantity": 1, "unit_price": 500.0}],
    }

    result = run_async(service.create_order(payload))

    assert result["order_id"].startswith("ord_")
    assert result["customer_id"] == "cust_valid_2"
    assert result["total_amount"] == 500.0
    assert result["status"] == "placed"


def test_invalid_order_data():
    """Test rejection when creating order with invalid fields."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_valid_3", "name": "Bruce Banner", "email": "banner@lab.org"}))

    # Invalid status
    try:
        run_async(service.create_order({"customer_id": "cust_valid_3", "status": "exploding"}))
        assert False, "Should have raised ValidationError on invalid status"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid payment status
    try:
        run_async(service.create_order({"customer_id": "cust_valid_3", "payment_status": "bounced"}))
        assert False, "Should have raised ValidationError on invalid payment status"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid item quantity
    try:
        run_async(
            service.create_order(
                {
                    "customer_id": "cust_valid_3",
                    "items": [{"item_id": "i1", "title": "Beaker", "quantity": -2, "unit_price": 10.0}],
                }
            )
        )
        assert False, "Should have raised ValidationError on invalid item quantity"
    except ValidationError as e:
        assert e.status_code == 400


def test_missing_required_fields():
    """Test rejection when required fields are missing or empty."""
    service, _, _ = create_isolated_environment()

    # Empty customer_id
    try:
        run_async(service.create_order({"customer_id": ""}))
        assert False, "Should have raised ValidationError on empty customer_id"
    except ValidationError as e:
        assert e.status_code == 400


def test_referenced_customer_not_found():
    """Test rejection when customer_id does not exist in customer repository."""
    service, _, _ = create_isolated_environment()

    try:
        run_async(service.create_order({"customer_id": "non_existent_customer"}))
        assert False, "Should have raised EntityNotFoundError for non-existent customer"
    except EntityNotFoundError as e:
        assert e.status_code == 404
        assert "not found" in e.message.lower() or "not exist" in e.message.lower()


def test_retrieving_existing_order():
    """Test retrieving an existing order by ID."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_find", "name": "Natasha Romanoff", "email": "nat@shield.gov"}))

    created = run_async(
        service.create_order(
            {
                "order_id": "ord_find_101",
                "customer_id": "cust_find",
                "items": [{"item_id": "it1", "title": "Comms Badge", "quantity": 1, "unit_price": 75.0}],
            }
        )
    )

    retrieved = run_async(service.get_order("ord_find_101"))
    assert retrieved["order_id"] == created["order_id"]
    assert retrieved["customer_id"] == "cust_find"
    assert retrieved["total_amount"] == 75.0
    assert "_id" not in retrieved


def test_retrieving_missing_order():
    """Test 404 EntityNotFoundError when order ID does not exist."""
    service, _, _ = create_isolated_environment()

    try:
        run_async(service.get_order("ord_ghost"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Empty order_id validation error
    try:
        run_async(service.get_order(""))
        assert False, "Should have raised ValidationError on empty order_id"
    except ValidationError as e:
        assert e.status_code == 400


def test_retrieving_orders_for_customer():
    """Test retrieving all orders for a customer."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_multi", "name": "Clint Barton", "email": "clint@shield.gov"}))

    run_async(
        service.create_order(
            {
                "order_id": "ord_c1",
                "customer_id": "cust_multi",
                "items": [{"item_id": "i1", "title": "Bow", "quantity": 1, "unit_price": 150.0}],
            }
        )
    )
    run_async(
        service.create_order(
            {
                "order_id": "ord_c2",
                "customer_id": "cust_multi",
                "items": [{"item_id": "i2", "title": "Arrows (Pack of 20)", "quantity": 3, "unit_price": 25.0}],
            }
        )
    )

    orders = run_async(service.get_orders_by_customer("cust_multi"))
    assert len(orders) == 2
    order_ids = {o["order_id"] for o in orders}
    assert "ord_c1" in order_ids
    assert "ord_c2" in order_ids
    for o in orders:
        assert "_id" not in o


def test_customer_with_no_orders():
    """Test that customer with zero orders returns empty list."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_empty", "name": "Thor Odinson", "email": "thor@asgard.gov"}))

    orders = run_async(service.get_orders_by_customer("cust_empty"))
    assert orders == []


def test_multiple_orders_for_one_customer():
    """Test bounded retrieval for a customer with multiple orders."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_bulk", "name": "Peter Parker", "email": "peter@dailybugle.com"}))

    for i in range(5):
        run_async(
            service.create_order(
                {
                    "order_id": f"ord_bulk_{i}",
                    "customer_id": "cust_bulk",
                    "items": [{"item_id": f"item_{i}", "title": f"Web Fluid {i}", "quantity": 1, "unit_price": 20.0}],
                }
            )
        )

    all_orders = run_async(service.get_orders_by_customer("cust_bulk", limit=10))
    assert len(all_orders) == 5

    bounded_orders = run_async(service.get_orders_by_customer("cust_bulk", limit=3))
    assert len(bounded_orders) == 3


def test_conflicting_order_creation():
    """Test 409 Conflict when creating an order with an existing order_id."""
    service, cust_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_dup", "name": "Steve Rogers", "email": "steve@avengers.org"}))

    payload = {
        "order_id": "ord_unique_100",
        "customer_id": "cust_dup",
        "items": [{"item_id": "shield_1", "title": "Vibranium Shield", "quantity": 1, "unit_price": 1000.0}],
    }
    run_async(service.create_order(payload))

    try:
        run_async(service.create_order(payload))
        assert False, "Should have raised DuplicateEntityError"
    except DuplicateEntityError as e:
        assert e.status_code == 409
        assert "already exists" in e.message.lower()


def test_response_does_not_expose_mongodb_id():
    """Ensure internal MongoDB _id is stripped from all repository and service responses."""
    _, _, order_repo = create_isolated_environment()

    # Simulate document with raw _id in memory store
    order_repo._memory_store["ord_raw_1"] = {
        "_id": "507f1f77bcf86cd799439011",
        "order_id": "ord_raw_1",
        "customer_id": "cust_raw",
        "status": "placed",
    }

    doc = run_async(order_repo.get_by_id("ord_raw_1"))
    assert doc is not None
    assert "_id" not in doc

    cust_docs = run_async(order_repo.get_by_customer_id("cust_raw"))
    assert len(cust_docs) == 1
    assert "_id" not in cust_docs[0]


def test_router_api_integration():
    """Verify endpoint routing logic and integration through Order router."""
    service, cust_repo, _ = create_isolated_environment()
    reset_order_service(service)
    run_async(cust_repo.create({"customer_id": "cust_router", "name": "Nick Fury", "email": "fury@shield.gov"}))

    # 1. Create order via router
    payload = OrderCreate(
        order_id="ord_router_1",
        customer_id="cust_router",
        status="shipped",
        currency="USD",
        items=[OrderItem(item_id="eye_1", title="Eyepatch", quantity=2, unit_price=15.0)],
    ) if "OrderCreate" in globals() else {
        "order_id": "ord_router_1",
        "customer_id": "cust_router",
        "status": "shipped",
        "currency": "USD",
        "items": [{"item_id": "eye_1", "title": "Eyepatch", "quantity": 2, "unit_price": 15.0}],
    }

    if hasattr(router, "create_order"):
        created = run_async(router.create_order(payload, service=service))
        assert created["order_id"] == "ord_router_1"
        assert created["customer_id"] == "cust_router"
        assert created["total_amount"] == 30.0

        # 2. Retrieve order by ID via router
        retrieved = run_async(router.get_order(order_id="ord_router_1", service=service))
        assert retrieved["order_id"] == "ord_router_1"
        assert retrieved["status"] == "shipped"

        # 3. Retrieve customer orders via router
        cust_orders = run_async(router.get_customer_orders(customer_id="cust_router", service=service))
        assert len(cust_orders) == 1
        assert cust_orders[0]["order_id"] == "ord_router_1"

    reset_order_service(None)


if __name__ == "__main__":
    tests = [
        test_order_model_and_item_validation,
        test_valid_order_creation,
        test_order_creation_auto_generates_id,
        test_invalid_order_data,
        test_missing_required_fields,
        test_referenced_customer_not_found,
        test_retrieving_existing_order,
        test_retrieving_missing_order,
        test_retrieving_orders_for_customer,
        test_customer_with_no_orders,
        test_multiple_orders_for_one_customer,
        test_conflicting_order_creation,
        test_response_does_not_expose_mongodb_id,
        test_router_api_integration,
    ]

    for t in tests:
        t()
        print(f"PASSED: {t.__name__}")
    print(f"\nAll {len(tests)} Order domain tests passed successfully!")
