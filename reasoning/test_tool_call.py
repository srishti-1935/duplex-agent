import pytest

from reasoning.tool_call import build_tool_call
from schemas import ActionType


def test_build_search_flights_call():
    action = build_tool_call(
        "search_flights",
        {
            "destination": "Delhi",
            "date": "2026-10-10",
        },
    )

    assert action.type == ActionType.TOOL_CALL
    assert action.tool_name == "search_flights"
    assert action.tool_args == {
        "destination": "Delhi",
        "date": "2026-10-10",
    }
    assert action.revision == 1


def test_build_call_with_optional_slot():
    action = build_tool_call(
        "book_flight",
        {
            "passenger_name": "Palak",
        },
        revision=2,
    )

    assert action.type == ActionType.TOOL_CALL
    assert action.tool_name == "book_flight"
    assert action.tool_args == {
        "passenger_name": "Palak",
    }
    assert action.revision == 2


def test_missing_required_slot_raises_error():
    with pytest.raises(ValueError, match="Missing required slots"):
        build_tool_call(
            "search_flights",
            {
                "destination": "Delhi",
            },
        )
