from reasoning.validator import validate_tool_args


def test_valid_search_flights():
    valid, missing, args = validate_tool_args(
        "search_flights",
        {
            "destination": "Delhi",
            "date": "2026-10-10",
        },
    )

    assert valid is True
    assert missing == []
    assert args == {
        "destination": "Delhi",
        "date": "2026-10-10",
    }


def test_missing_required_slot():
    valid, missing, args = validate_tool_args(
        "search_flights",
        {
            "destination": "Delhi",
        },
    )

    assert valid is False
    assert missing == ["date"]
    assert args == {
        "destination": "Delhi",
    }


def test_optional_slot():
    valid, missing, args = validate_tool_args(
        "book_flight",
        {
            "passenger_name": "Palak",
            "flight_id": "FL123",
        },
    )

    assert valid is True
    assert missing == []
    assert args == {
        "passenger_name": "Palak",
        "flight_id": "FL123",
    }


def test_optional_slot_can_be_omitted():
    valid, missing, args = validate_tool_args(
        "book_flight",
        {
            "passenger_name": "Palak",
        },
    )

    assert valid is True
    assert missing == []
    assert args == {
        "passenger_name": "Palak",
    }


def test_extra_slots_are_removed():
    valid, missing, args = validate_tool_args(
        "track_order",
        {
            "order_id": "ORD123",
            "random_value": "ignore me",
        },
    )

    assert valid is True
    assert missing == []
    assert args == {
        "order_id": "ORD123",
    }


def test_unknown_tool():
    valid, missing, args = validate_tool_args(
        "unknown_tool",
        {
            "value": "test",
        },
    )

    assert valid is False
    assert missing == ["unknown_tool"]
    assert args == {}
