from reasoning.self_correction import (
    correct_tool_args,
    should_retry,
)


def test_correct_missing_slot():
    result = correct_tool_args(
        "search_flights",
        {
            "destination": "Delhi",
        },
        "missing required argument: date",
        {
            "date": "2026-10-10",
        },
    )

    assert result.corrected is True
    assert result.slots == {
        "destination": "Delhi",
        "date": "2026-10-10",
    }


def test_correction_without_fix_fails():
    result = correct_tool_args(
        "search_flights",
        {
            "destination": "Delhi",
        },
        "missing required argument: date",
    )

    assert result.corrected is False
    assert result.slots == {
        "destination": "Delhi",
    }


def test_invalid_correction_fails():
    result = correct_tool_args(
        "search_flights",
        {
            "destination": "Delhi",
        },
        "missing required argument: date",
        {
            "wrong_slot": "value",
        },
    )

    assert result.corrected is False
    assert "date" in result.reason


def test_retry_allowed_after_correction():
    assert should_retry(True, 0) is True


def test_retry_stops_at_limit():
    assert should_retry(True, 1) is False


def test_failed_correction_is_not_retried():
    assert should_retry(False, 0) is False
