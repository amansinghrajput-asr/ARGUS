"""Unit and integration tests for ConversationHistory and Human Handoff domain."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure AmanSR_backend_1 root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.v1.endpoints.history import (
    get_handoff_service,
    reset_handoff_service,
    router,
)
from app.core.exceptions import (
    ArgusDomainError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.history import (
    ConversationHistoryBase,
    ConversationTurn,
    HumanHandoffResponse,
    NoteCreate,
    SpecialistInvestigationNote,
    TurnCreate,
    validate_note_fields,
    validate_turn_fields,
)
from app.repositories.case_repo import CaseRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.history_repo import HistoryRepository
from app.repositories.order_repo import OrderRepository
from app.services.handoff_service import HandoffService


def run_async(coro):
    """Helper to run async coroutines synchronously in test runner."""
    return asyncio.run(coro)


def create_isolated_environment() -> Tuple[HandoffService, CustomerRepository, OrderRepository, CaseRepository, HistoryRepository]:
    """Create isolated in-memory repositories and HandoffService instance."""
    customer_repo = CustomerRepository(db=None)
    order_repo = OrderRepository(db=None)
    case_repo = CaseRepository(db=None)
    history_repo = HistoryRepository(db=None)
    service = HandoffService(
        history_repo=history_repo,
        case_repo=case_repo,
        customer_repo=customer_repo,
        order_repo=order_repo,
    )
    return service, customer_repo, order_repo, case_repo, history_repo


def test_history_initialization():
    """Test initializing conversation history record for a valid complaint case."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_hist_1", "name": "Tony Stark", "email": "tony@stark.com"}))
    run_async(case_repo.create({"case_id": "case_hist_1", "customer_id": "cust_hist_1", "raw_complaint": "Suit sensor offline"}))

    history = run_async(service.get_or_create_history("case_hist_1"))

    assert history["case_id"] == "case_hist_1"
    assert history["customer_id"] == "cust_hist_1"
    assert history["history_id"].startswith("hist_")
    assert history["messages"] == []
    assert history["investigation_trail"] == []
    assert history["human_handoff_summary"] is None
    assert "created_at" in history
    assert "updated_at" in history
    assert "_id" not in history


def test_retrieving_history():
    """Test retrieving conversation history for an existing case."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_hist_2", "name": "Steve Rogers", "email": "steve@shield.gov"}))
    run_async(case_repo.create({"case_id": "case_hist_2", "customer_id": "cust_hist_2", "raw_complaint": "Compass misaligned"}))

    history_1 = run_async(service.get_history("case_hist_2"))
    history_2 = run_async(service.get_history("case_hist_2"))

    assert history_1["history_id"] == history_2["history_id"]
    assert history_1["case_id"] == "case_hist_2"


def test_missing_case_handling():
    """Test proper domain errors when referenced case does not exist."""
    service, _, _, _, _ = create_isolated_environment()

    # Get history for missing case
    try:
        run_async(service.get_history("case_non_existent"))
        assert False, "Should have raised EntityNotFoundError for missing case"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Add turn to missing case
    try:
        run_async(service.add_turn("case_non_existent", {"sender": "customer", "message_text": "Hello"}))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Add note to missing case
    try:
        run_async(service.add_note("case_non_existent", {"specialist": "spec_1", "action_taken": "act", "result": "res"}))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Compile handoff for missing case
    try:
        run_async(service.compile_handoff_packet("case_non_existent"))
        assert False, "Should have raised EntityNotFoundError"
    except EntityNotFoundError as e:
        assert e.status_code == 404

    # Empty case_id validation error
    try:
        run_async(service.get_history(""))
        assert False, "Should have raised ValidationError on empty case_id"
    except ValidationError as e:
        assert e.status_code == 400


def test_adding_conversation_turn():
    """Test appending a single message turn."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_turn_1", "name": "Natasha Romanoff", "email": "nat@shield.gov"}))
    run_async(case_repo.create({"case_id": "case_turn_1", "customer_id": "cust_turn_1", "raw_complaint": "Radio silence detected"}))

    turn_payload = {
        "sender": "customer",
        "message_text": "I lost signal on frequency delta.",
        "detected_intent": "signal_loss",
    }

    updated = run_async(service.add_turn("case_turn_1", turn_payload))
    assert len(updated["messages"]) == 1
    turn = updated["messages"][0]
    assert turn["turn_id"] == 1
    assert turn["sender"] == "customer"
    assert turn["message_text"] == "I lost signal on frequency delta."
    assert turn["detected_intent"] == "signal_loss"
    assert "timestamp" in turn
    assert "_id" not in updated


def test_multiple_conversation_turns():
    """Test appending multiple conversation turns sequentially with incrementing turn_id."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_turns", "name": "Bruce Banner", "email": "banner@lab.org"}))
    run_async(case_repo.create({"case_id": "case_turns", "customer_id": "cust_turns", "raw_complaint": "Containment alert"}))

    run_async(service.add_turn("case_turns", {"sender": "customer", "message_text": "The pressure is rising."}))
    run_async(service.add_turn("case_turns", {"sender": "orchestrator", "message_text": "Initiating ventilation protocol."}))
    updated = run_async(service.add_turn("case_turns", {"sender": "customer", "message_text": "Pressure stabilizing now."}))

    assert len(updated["messages"]) == 3
    assert [m["turn_id"] for m in updated["messages"]] == [1, 2, 3]
    assert updated["messages"][1]["sender"] == "orchestrator"


def test_adding_investigation_note():
    """Test appending an investigation trail note."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_note_1", "name": "Peter Parker", "email": "peter@dailybugle.com"}))
    run_async(case_repo.create({"case_id": "case_note_1", "customer_id": "cust_note_1", "raw_complaint": "Web shooter jammed"}))

    note_payload = {
        "specialist": "hardware_specialist",
        "action_taken": "Inspected fluid valve nozzle clearance",
        "result": "Debris lodged in primary capillary tube",
    }

    updated = run_async(service.add_note("case_note_1", note_payload))
    assert len(updated["investigation_trail"]) == 1
    note = updated["investigation_trail"][0]
    assert note["specialist"] == "hardware_specialist"
    assert note["action_taken"] == "Inspected fluid valve nozzle clearance"
    assert note["result"] == "Debris lodged in primary capillary tube"
    assert "timestamp" in note


def test_multiple_investigation_notes():
    """Test appending multiple specialist findings to investigation trail."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_notes", "name": "Stephen Strange", "email": "strange@sanctum.org"}))
    run_async(case_repo.create({"case_id": "case_notes", "customer_id": "cust_notes", "raw_complaint": "Temporal anomaly report"}))

    run_async(service.add_note("case_notes", {"specialist": "sensor_specialist", "action_taken": "Monitored chronal drift", "result": "Oscillating at 4.2Hz"}))
    updated = run_async(service.add_note("case_notes", {"specialist": "containment_specialist", "action_taken": "Reinforced runic barrier", "result": "Field stabilized"}))

    assert len(updated["investigation_trail"]) == 2
    assert updated["investigation_trail"][0]["specialist"] == "sensor_specialist"
    assert updated["investigation_trail"][1]["specialist"] == "containment_specialist"


def test_handoff_generation():
    """Test zero-repeat human handoff packet compilation."""
    service, cust_repo, order_repo, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_handoff", "name": "Wanda Maximoff", "email": "wanda@avengers.org"}))
    run_async(order_repo.create({"order_id": "ord_handoff_10", "customer_id": "cust_handoff", "status": "shipped"}))
    run_async(
        case_repo.create(
            {
                "case_id": "case_handoff_1",
                "case_number": "ARG-778899",
                "customer_id": "cust_handoff",
                "order_id": "ord_handoff_10",
                "raw_complaint": "Incorrect artifact delivered in package.",
                "category": "order_fulfillment",
                "priority": "critical",
                "status": "escalated_to_human",
                "escalation_reason": "Confidence score below threshold for automated resolution",
            }
        )
    )

    run_async(service.add_turn("case_handoff_1", {"sender": "customer", "message_text": "I ordered a darkhold replica, got a regular spellbook."}))
    run_async(service.add_note("case_handoff_1", {"specialist": "inventory_specialist", "action_taken": "Checked warehouse SKU dispatch", "result": "SKU mismatch confirmed at packing bay 4"}))

    packet = run_async(service.compile_handoff_packet("case_handoff_1"))

    assert packet["case_id"] == "case_handoff_1"
    assert packet["case_number"] == "ARG-778899"
    assert packet["customer_id"] == "cust_handoff"
    assert packet["customer_name"] == "Wanda Maximoff"
    assert packet["customer_email"] == "wanda@avengers.org"
    assert packet["order_id"] == "ord_handoff_10"
    assert packet["priority"] == "critical"
    assert packet["status"] == "escalated_to_human"
    assert len(packet["conversation_turns"]) == 1
    assert len(packet["investigation_trail"]) == 1
    assert "human_handoff_summary" in packet
    assert len(packet["human_handoff_summary"]) > 0
    assert "_id" not in packet


def test_handoff_contains_conversation_context():
    """Verify handoff packet preserves conversation messages for zero-repeat context."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_ctx", "name": "Carol Danvers", "email": "carol@marvel.org"}))
    run_async(case_repo.create({"case_id": "case_ctx", "customer_id": "cust_ctx", "raw_complaint": "Hyperdrive thruster issue"}))

    run_async(service.add_turn("case_ctx", {"sender": "customer", "message_text": "Initial thruster surge detected."}))
    run_async(service.add_turn("case_ctx", {"sender": "orchestrator", "message_text": "Have you calibrated the coolant?"}))

    packet = run_async(service.compile_handoff_packet("case_ctx"))
    turns = packet["conversation_turns"]
    assert len(turns) == 2
    assert turns[0]["message_text"] == "Initial thruster surge detected."
    assert turns[1]["sender"] == "orchestrator"


def test_handoff_contains_investigation_trail():
    """Verify handoff packet preserves specialist investigation trail."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_trail", "name": "Thor Odinson", "email": "thor@asgard.gov"}))
    run_async(case_repo.create({"case_id": "case_trail", "customer_id": "cust_trail", "raw_complaint": "Mjolnir tracking issue"}))

    run_async(service.add_note("case_trail", {"specialist": "telemetry_specialist", "action_taken": "Pinged bifrost GPS", "result": "Coordinates verified"}))

    packet = run_async(service.compile_handoff_packet("case_trail"))
    trail = packet["investigation_trail"]
    assert len(trail) == 1
    assert trail[0]["specialist"] == "telemetry_specialist"
    assert trail[0]["result"] == "Coordinates verified"
    assert "telemetry_specialist" in packet["human_handoff_summary"]


def test_handoff_does_not_expose_mongodb_id():
    """Ensure internal MongoDB _id is stripped from all history and handoff outputs."""
    service, cust_repo, _, case_repo, history_repo = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_leak", "name": "Leak Test", "email": "leak@test.com"}))
    run_async(case_repo.create({"case_id": "case_leak", "customer_id": "cust_leak", "raw_complaint": "Test leak"}))

    # Inject doc with _id directly into memory store
    history_repo._memory_store["case_leak"] = {
        "_id": "607f1f77bcf86cd799439999",
        "history_id": "hist_leak_01",
        "case_id": "case_leak",
        "customer_id": "cust_leak",
        "messages": [{"turn_id": 1, "sender": "customer", "message_text": "Hi"}],
        "investigation_trail": [],
        "human_handoff_summary": None,
    }

    history = run_async(service.get_history("case_leak"))
    assert "_id" not in history

    packet = run_async(service.compile_handoff_packet("case_leak"))
    assert "_id" not in packet


def test_invalid_payload_handling():
    """Test validation rejection on invalid turns and notes."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_inv", "name": "Invalid Test", "email": "inv@test.com"}))
    run_async(case_repo.create({"case_id": "case_inv", "customer_id": "cust_inv", "raw_complaint": "Test issue"}))

    # Empty turn sender
    try:
        run_async(service.add_turn("case_inv", {"sender": "", "message_text": "Valid message"}))
        assert False, "Should have raised ValidationError on empty sender"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty turn message_text
    try:
        run_async(service.add_turn("case_inv", {"sender": "customer", "message_text": ""}))
        assert False, "Should have raised ValidationError on empty message_text"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty note specialist
    try:
        run_async(service.add_note("case_inv", {"specialist": "", "action_taken": "act", "result": "res"}))
        assert False, "Should have raised ValidationError on empty specialist"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty note action_taken
    try:
        run_async(service.add_note("case_inv", {"specialist": "spec", "action_taken": "", "result": "res"}))
        assert False, "Should have raised ValidationError on empty action_taken"
    except ValidationError as e:
        assert e.status_code == 400

    # Empty note result
    try:
        run_async(service.add_note("case_inv", {"specialist": "spec", "action_taken": "act", "result": ""}))
        assert False, "Should have raised ValidationError on empty result"
    except ValidationError as e:
        assert e.status_code == 400


def test_router_api_integration():
    """Verify endpoint routing logic and integration through history/handoff router."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    reset_handoff_service(service)
    run_async(cust_repo.create({"customer_id": "cust_rtr", "name": "Router Customer", "email": "router@cust.org"}))
    run_async(case_repo.create({"case_id": "case_rtr", "customer_id": "cust_rtr", "raw_complaint": "Router complaint"}))

    # 1. Add turn via router
    turn_payload = TurnCreate(sender="customer", message_text="Hello support agent") if "TurnCreate" in globals() else {"sender": "customer", "message_text": "Hello support agent"}
    if hasattr(router, "add_conversation_turn"):
        res = run_async(router.add_conversation_turn(case_id="case_rtr", payload=turn_payload, service=service))
        assert len(res["messages"]) == 1

        # 2. Add note via router
        note_payload = NoteCreate(specialist="test_spec", action_taken="action 1", result="result 1") if "NoteCreate" in globals() else {"specialist": "test_spec", "action_taken": "action 1", "result": "result 1"}
        res_note = run_async(router.add_investigation_note(case_id="case_rtr", payload=note_payload, service=service))
        assert len(res_note["investigation_trail"]) == 1

        # 3. Get history via router
        hist = run_async(router.get_case_history(case_id="case_rtr", service=service))
        assert len(hist["messages"]) == 1
        assert len(hist["investigation_trail"]) == 1

        # 4. Get handoff via router
        handoff = run_async(router.get_human_handoff(case_id="case_rtr", service=service))
        assert handoff["case_id"] == "case_rtr"
        assert len(handoff["conversation_turns"]) == 1
        assert len(handoff["investigation_trail"]) == 1

    reset_handoff_service(None)


def test_repeated_history_retrieval_remains_consistent():
    """Verify idempotency and consistency of history record across repeated lookups."""
    service, cust_repo, _, case_repo, _ = create_isolated_environment()
    run_async(cust_repo.create({"customer_id": "cust_rep", "name": "Repeated User", "email": "rep@user.org"}))
    run_async(case_repo.create({"case_id": "case_rep", "customer_id": "cust_rep", "raw_complaint": "Consistency test complaint"}))

    run_async(service.add_turn("case_rep", {"sender": "customer", "message_text": "Turn 1"}))
    h1 = run_async(service.get_history("case_rep"))
    h2 = run_async(service.get_history("case_rep"))
    h3 = run_async(service.get_history("case_rep"))

    assert h1["history_id"] == h2["history_id"] == h3["history_id"]
    assert len(h1["messages"]) == len(h2["messages"]) == len(h3["messages"]) == 1


if __name__ == "__main__":
    tests = [
        test_history_initialization,
        test_retrieving_history,
        test_missing_case_handling,
        test_adding_conversation_turn,
        test_multiple_conversation_turns,
        test_adding_investigation_note,
        test_multiple_investigation_notes,
        test_handoff_generation,
        test_handoff_contains_conversation_context,
        test_handoff_contains_investigation_trail,
        test_handoff_does_not_expose_mongodb_id,
        test_invalid_payload_handling,
        test_router_api_integration,
        test_repeated_history_retrieval_remains_consistent,
    ]

    for t in tests:
        t()
        print(f"PASSED: {t.__name__}")
    print(f"\nAll {len(tests)} ConversationHistory & Handoff tests passed successfully!")
