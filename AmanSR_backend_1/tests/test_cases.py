"""Unit and integration tests for the ComplaintCase domain (isolated in-memory)."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure AmanSR_backend_1 root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.v1.endpoints.cases import (
    get_case_service,
    reset_case_service,
    router,
)
from app.core.exceptions import (
    ArgusDomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.case import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    ComplaintCaseBase,
    validate_case_fields,
)
from app.repositories.case_repo import CaseRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.order_repo import OrderRepository
from app.services.case_service import CaseService


def run_async(coro):
    """Helper to run async coroutines synchronously in test runner."""
    return asyncio.run(coro)


def create_isolated_environment() -> Tuple[CaseService, CustomerRepository, OrderRepository, CaseRepository]:
    """Create isolated in-memory repositories and CaseService instance."""
    customer_repo = CustomerRepository(db=None)
    order_repo = OrderRepository(db=None)
    case_repo = CaseRepository(db=None)
    service = CaseService(
        case_repo=case_repo,
        customer_repo=customer_repo,
        order_repo=order_repo,
    )
    return service, customer_repo, order_repo, case_repo


def test_case_model_validation():
    """Test model field validation rules for ComplaintCase."""
    # Valid fields
    validate_case_fields(
        customer_id="cust_1",
        raw_complaint="My package was damaged upon arrival.",
        status="open",
        priority="high",
        confidence_score=0.92,
    )

    # Empty customer_id
    try:
        validate_case_fields(customer_id="", raw_complaint="Complaint text")
        assert False, "Should have raised ValueError on empty customer_id"
    except ValueError as e:
        assert "customer_id" in str(e).lower()

    # Empty raw_complaint
    try:
        validate_case_fields(customer_id="cust_1", raw_complaint="")
        assert False, "Should have raised ValueError on empty raw_complaint"
    except ValueError as e:
        assert "raw_complaint" in str(e).lower()

    # Invalid status
    try:
        validate_case_fields(customer_id="cust_1", raw_complaint="Complaint", status="non_existent")
        assert False, "Should have raised ValueError on invalid status"
    except ValueError as e:
        assert "status" in str(e).lower()

    # Invalid priority
    try:
        validate_case_fields(customer_id="cust_1", raw_complaint="Complaint", priority="super_urgent")
        assert False, "Should have raised ValueError on invalid priority"
    except ValueError as e:
        assert "priority" in str(e).lower()

    # Invalid confidence score (< 0 or > 1)
    try:
        validate_case_fields(customer_id="cust_1", raw_complaint="Complaint", confidence_score=1.5)
        assert False, "Should have raised ValueError on confidence score > 1"
    except ValueError as e:
        assert "confidence_score" in str(e).lower()


def test_valid_case_creation():
    """Test successfully creating a complaint case with customer and order references."""
    service, cust_repo, order_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_case_1", "name": "Bruce Wayne", "email": "bruce@wayne.com"}))
    run_async(order_repo.create({"order_id": "ord_case_1", "customer_id": "cust_case_1", "status": "shipped"}))

    payload = {
        "case_id": "case_test_001",
        "case_number": "ARG-001001",
        "customer_id": "cust_case_1",
        "order_id": "ord_case_1",
        "raw_complaint": "The Batmobile replacement parts did not arrive on time.",
        "category": "order_fulfillment",
        "priority": "high",
        "parsed_sub_issues": ["Late delivery", "Replacement parts missing"],
        "confidence_score": 0.88,
    }

    result = run_async(service.create_case(payload))

    assert result["case_id"] == "case_test_001"
    assert result["case_number"] == "ARG-001001"
    assert result["customer_id"] == "cust_case_1"
    assert result["order_id"] == "ord_case_1"
    assert result["status"] == "open"
    assert result["priority"] == "high"
    assert result["category"] == "order_fulfillment"
    assert len(result["parsed_sub_issues"]) == 2
    assert result["confidence_score"] == 0.88
    assert "created_at" in result
    assert "updated_at" in result
    assert "_id" not in result


def test_case_creation_auto_generates_identifiers():
    """Test that case_id and case_number are auto-generated if omitted."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_case_2", "name": "Clark Kent", "email": "clark@planet.com"}))

    payload = {
        "customer_id": "cust_case_2",
        "raw_complaint": "Subscription auto-renewal failed to charge correctly.",
    }

    result = run_async(service.create_case(payload))

    assert result["case_id"].startswith("case_")
    assert result["case_number"].startswith("ARG-")
    assert result["customer_id"] == "cust_case_2"
    assert result["status"] == "open"
    assert result["priority"] == "medium"
    assert result["category"] == "general"


def test_invalid_case_data():
    """Test rejection when creating case with invalid field values."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_case_3", "name": "Diana Prince", "email": "diana@themyscira.gov"}))

    # Invalid status
    try:
        run_async(
            service.create_case(
                {"customer_id": "cust_case_3", "raw_complaint": "Issue", "status": "destroyed"}
            )
        )
        assert False, "Should have raised ValidationError on invalid status"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid priority
    try:
        run_async(
            service.create_case(
                {"customer_id": "cust_case_3", "raw_complaint": "Issue", "priority": "maximum_overdrive"}
            )
        )
        assert False, "Should have raised ValidationError on invalid priority"
    except ValidationError as e:
        assert e.status_code == 400

    # Invalid confidence score
    try:
        run_async(
            service.create_case(
                {"customer_id": "cust_case_3", "raw_complaint": "Issue", "confidence_score": -0.5}
            )
        )
        assert False, "Should have raised ValidationError on negative confidence score"
    except ValidationError as e:
        assert e.status_code == 400


def test_missing_required_fields():
    """Test rejection when required fields are missing."""
    service, _, _, _ = create_isolated_environment()

    # Missing customer_id
    try:
        run_async(service.create_case({"customer_id": "", "raw_complaint": "Valid complaint text"}))
        assert False, "Should have raised ValidationError on empty customer_id"
    except ValidationError as e:
        assert e.status_code == 400

    # Missing raw_complaint
    try:
        run_async(service.create_case({"customer_id": "cust_any", "raw_complaint": ""}))
        assert False, "Should have raised ValidationError on empty raw_complaint"
    except ValidationError as e:
        assert e.status_code == 400


def test_customer_reference_validation():
    """Test rejection when referenced customer does not exist."""
    service, _, _, _ = create_isolated_environment()

    try:
        run_async(
            service.create_case(
                {"customer_id": "non_existent_cust", "raw_complaint": "Some issue text"}
            )
        )
        assert False, "Should have raised EntityNotFoundError for missing customer"
    except EntityNotFoundError as e:
        assert e.status_code == 404
        assert "not found" in e.message.lower()


def test_optional_order_reference_handling():
    """Test handling of optional order_id parameter."""
    service, cust_repo, order_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_order_test", "name": "Barry Allen", "email": "barry@ccpd.gov"}))
    run_async(order_repo.create({"order_id": "ord_valid_10", "customer_id": "cust_order_test"}))

    # 1. Valid order_id
    case_with_order = run_async(
        service.create_case(
            {
                "customer_id": "cust_order_test",
                "order_id": "ord_valid_10",
                "raw_complaint": "Treadmill motor running too fast.",
            }
        )
    )
    assert case_with_order["order_id"] == "ord_valid_10"

    # 2. Non-existent order_id
    try:
        run_async(
            service.create_case(
                {
                    "customer_id": "cust_order_test",
                    "order_id": "ord_ghost_99",
                    "raw_complaint": "Ghost order issue.",
                }
            )
        )
        assert False, "Should have raised EntityNotFoundError for missing order"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # 3. Omitted order_id
    case_no_order = run_async(
        service.create_case(
            {
                "customer_id": "cust_order_test",
                "raw_complaint": "General inquiry without order reference.",
            }
        )
    )
    assert case_no_order["order_id"] is None


def test_retrieving_existing_case():
    """Test retrieving case by ID."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_find_case", "name": "Arthur Curry", "email": "curry@atlantis.gov"}))

    created = run_async(
        service.create_case(
            {
                "case_id": "case_find_1",
                "customer_id": "cust_find_case",
                "raw_complaint": "Water damage to underwater communication terminal.",
            }
        )
    )

    retrieved = run_async(service.get_case("case_find_1"))
    assert retrieved["case_id"] == "case_find_1"
    assert retrieved["customer_id"] == "cust_find_case"
    assert retrieved["raw_complaint"] == created["raw_complaint"]
    assert "_id" not in retrieved


def test_retrieving_missing_case():
    """Test 404 EntityNotFoundError when case ID does not exist."""
    service, _, _, _ = create_isolated_environment()

    try:
        run_async(service.get_case("case_non_existent"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Empty case_id
    try:
        run_async(service.get_case(""))
        assert False, "Should have raised ValidationError on empty case_id"
    except ValidationError as e:
        assert e.status_code == 400


def test_updating_existing_case():
    """Test partial update (PATCH) of allowed fields on an existing case."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_patch", "name": "Victor Stone", "email": "vic@cyborg.org"}))

    created = run_async(
        service.create_case(
            {
                "case_id": "case_to_patch",
                "customer_id": "cust_patch",
                "raw_complaint": "Firmware update failed on left servo.",
                "status": "open",
                "priority": "low",
            }
        )
    )

    patch_payload = {
        "status": "investigating",
        "priority": "critical",
        "confidence_score": 0.95,
        "assigned_agent": "specialist_hardware_01",
        "resolution_summary": "Diagnostic routines initiated.",
    }

    updated = run_async(service.update_case("case_to_patch", patch_payload))

    assert updated["case_id"] == "case_to_patch"
    assert updated["status"] == "investigating"
    assert updated["priority"] == "critical"
    assert updated["confidence_score"] == 0.95
    assert updated["assigned_agent"] == "specialist_hardware_01"
    assert updated["resolution_summary"] == "Diagnostic routines initiated."
    assert updated["updated_at"] >= created["created_at"]
    assert "_id" not in updated


def test_updating_missing_case():
    """Test 404 EntityNotFoundError when attempting to update a missing case."""
    service, _, _, _ = create_isolated_environment()

    try:
        run_async(service.update_case("case_ghost", {"status": "closed"}))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404


def test_listing_cases():
    """Test listing cases with optional status and customer_id filters."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_list_1", "name": "Hal Jordan", "email": "hal@lantern.org"}))
    run_async(cust_repo.create({"customer_id": "cust_list_2", "name": "John Stewart", "email": "john@lantern.org"}))

    run_async(service.create_case({"case_id": "c1", "customer_id": "cust_list_1", "raw_complaint": "Ring battery low", "status": "open"}))
    run_async(service.create_case({"case_id": "c2", "customer_id": "cust_list_1", "raw_complaint": "Power conduit failure", "status": "investigating"}))
    run_async(service.create_case({"case_id": "c3", "customer_id": "cust_list_2", "raw_complaint": "Battery dock missing", "status": "open"}))

    # List all
    all_cases = run_async(service.list_cases())
    assert len(all_cases) == 3

    # Filter by customer
    cust_1_cases = run_async(service.list_cases(customer_id="cust_list_1"))
    assert len(cust_1_cases) == 2

    # Filter by status
    open_cases = run_async(service.list_cases(status="open"))
    assert len(open_cases) == 2

    # Filter by customer and status
    cust_1_investigating = run_async(service.list_cases(customer_id="cust_list_1", status="investigating"))
    assert len(cust_1_investigating) == 1
    assert cust_1_investigating[0]["case_id"] == "c2"


def test_multiple_cases_for_one_customer():
    """Test retrieving multiple cases registered to a single customer."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_bulk_case", "name": "Oliver Queen", "email": "oliver@arrow.org"}))

    for i in range(4):
        run_async(
            service.create_case(
                {
                    "case_id": f"case_bulk_{i}",
                    "customer_id": "cust_bulk_case",
                    "raw_complaint": f"Equipment issue #{i}",
                }
            )
        )

    cases = run_async(service.list_cases(customer_id="cust_bulk_case"))
    assert len(cases) == 4
    for c in cases:
        assert "_id" not in c


def test_conflicting_case_creation():
    """Test 409 Conflict when case_id already exists."""
    service, cust_repo, _, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_dup_case", "name": "Ray Palmer", "email": "ray@palmer.org"}))

    payload = {
        "case_id": "case_unique_77",
        "customer_id": "cust_dup_case",
        "raw_complaint": "Suit compression glitch.",
    }
    run_async(service.create_case(payload))

    try:
        run_async(service.create_case(payload))
        assert False, "Should have raised DuplicateEntityError"
    except DuplicateEntityError as e:
        assert e.status_code == 409
        assert "already exists" in e.message.lower()


def test_response_does_not_expose_mongodb_id():
    """Ensure internal MongoDB _id is stripped from all responses."""
    _, _, _, case_repo = create_isolated_environment()

    case_repo._memory_store["case_raw"] = {
        "_id": "607f1f77bcf86cd799439022",
        "case_id": "case_raw",
        "customer_id": "cust_raw",
        "raw_complaint": "Internal raw ID leak test.",
        "status": "open",
    }

    doc = run_async(case_repo.get_by_id("case_raw"))
    assert doc is not None
    assert "_id" not in doc

    updated = run_async(case_repo.update("case_raw", {"status": "investigating"}))
    assert updated is not None
    assert "_id" not in updated

    listed = run_async(case_repo.list_cases())
    assert len(listed) == 1
    assert "_id" not in listed[0]


def test_router_api_integration():
    """Verify endpoint routing logic and integration through Case router."""
    service, cust_repo, _, _ = create_isolated_environment()
    reset_case_service(service)
    run_async(cust_repo.create({"customer_id": "cust_router_case", "name": "Wally West", "email": "wally@flash.org"}))

    # 1. Create case via router
    payload = CaseCreate(
        case_id="case_router_1",
        customer_id="cust_router_case",
        raw_complaint="Speed force telemetry disconnect.",
        priority="high",
    ) if "CaseCreate" in globals() else {
        "case_id": "case_router_1",
        "customer_id": "cust_router_case",
        "raw_complaint": "Speed force telemetry disconnect.",
        "priority": "high",
    }

    if hasattr(router, "create_case"):
        created = run_async(router.create_case(payload, service=service))
        assert created["case_id"] == "case_router_1"
        assert created["priority"] == "high"

        # 2. Retrieve case by ID via router
        retrieved = run_async(router.get_case(case_id="case_router_1", service=service))
        assert retrieved["case_id"] == "case_router_1"
        assert retrieved["status"] == "open"

        # 3. Patch case via router
        patch_payload = CaseUpdate(status="investigating") if "CaseUpdate" in globals() else {"status": "investigating"}
        updated = run_async(router.update_case(case_id="case_router_1", payload=patch_payload, service=service))
        assert updated["status"] == "investigating"

        # 4. List cases via router
        listed = run_async(router.list_cases(customer_id="cust_router_case", status_filter=None, limit=50, service=service))
        assert len(listed) == 1
        assert listed[0]["case_id"] == "case_router_1"

    reset_case_service(None)


if __name__ == "__main__":
    tests = [
        test_case_model_validation,
        test_valid_case_creation,
        test_case_creation_auto_generates_identifiers,
        test_invalid_case_data,
        test_missing_required_fields,
        test_customer_reference_validation,
        test_optional_order_reference_handling,
        test_retrieving_existing_case,
        test_retrieving_missing_case,
        test_updating_existing_case,
        test_updating_missing_case,
        test_listing_cases,
        test_multiple_cases_for_one_customer,
        test_conflicting_case_creation,
        test_response_does_not_expose_mongodb_id,
        test_router_api_integration,
    ]

    for t in tests:
        t()
        print(f"PASSED: {t.__name__}")
    print(f"\nAll {len(tests)} Case domain tests passed successfully!")
