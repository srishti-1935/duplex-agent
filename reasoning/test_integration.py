from reasoning import process_text
from schemas import ActionType


def test_complete_reasoning_flow():
    result = process_text(
        "Find flights to Delhi on October 10"
    )

    action = result.action

    assert action.type == ActionType.TOOL_CALL
    assert action.tool_name == "search_flights"
    assert action.tool_args == {
        "destination": "Delhi",
        "date": "October 10",
    }


def test_reasoning_flow_requests_missing_information():
    result = process_text(
        "Find flights to Delhi"
    )

    action = result.action

    assert action.type == ActionType.CLARIFICATION_REQUEST
    assert action.ambiguous_slots == ["date"]


def test_reasoning_flow_preserves_revision():
    result = process_text(
        "Book flight FL123 for Palak",
        revision=7,
    )

    assert result.action.revision == 7
    assert result.action.type == ActionType.TOOL_CALL
