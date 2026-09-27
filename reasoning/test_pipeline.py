from reasoning.pipeline import process_text
from schemas import ActionType


def test_complete_request_creates_tool_call():
    result = process_text(
        "Find flights to Delhi on October 10"
    )

    assert result.action.type == ActionType.TOOL_CALL
    assert result.action.tool_name == "search_flights"
    assert result.action.tool_args["destination"] == "Delhi"
    assert result.action.tool_args["date"] == "October 10"


def test_missing_slot_creates_clarification():
    result = process_text(
        "Find flights to Delhi"
    )

    assert result.action.type == ActionType.CLARIFICATION_REQUEST
    assert result.intent == "search_flights"
    assert "date" in result.missing_slots
    assert result.action.ambiguous_slots == ["date"]


def test_unknown_request_creates_clarification():
    result = process_text(
        "Tell me something interesting"
    )

    assert result.action.type == ActionType.CLARIFICATION_REQUEST
    assert result.intent is None


def test_book_flight_pipeline():
    result = process_text(
        "Book flight FL123 for Palak"
    )

    assert result.action.type == ActionType.TOOL_CALL
    assert result.action.tool_name == "book_flight"
    assert result.action.tool_args == {
        "flight_id": "FL123",
        "passenger_name": "Palak",
    }


def test_revision_is_preserved():
    result = process_text(
        "Find flights to Delhi on October 10",
        revision=5,
    )

    assert result.action.revision == 5
