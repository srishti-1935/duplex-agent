from reasoning.chain import (
    ChainPlan,
    apply_tool_result,
    get_next_step,
)


def test_add_tool_steps():
    plan = ChainPlan()

    first = plan.add_step(
        "search_flights",
        {
            "destination": "Delhi",
            "date": "2026-10-10",
        },
    )

    second = plan.add_step(
        "book_flight",
        {
            "passenger_name": "Palak",
            "flight_id": "FL123",
        },
    )

    assert first.revision == 1
    assert second.revision == 2
    assert len(plan.steps) == 2


def test_tool_result_updates_slots():
    slots = {
        "destination": "Delhi",
    }

    result = {
        "flight_id": "FL123",
    }

    updated = apply_tool_result(
        slots,
        result,
        {
            "flight_id": "flight_id",
        },
    )

    assert updated == {
        "destination": "Delhi",
        "flight_id": "FL123",
    }


def test_get_next_step():
    plan = ChainPlan()

    plan.add_step(
        "search_flights",
        {
            "destination": "Delhi",
            "date": "2026-10-10",
        },
    )

    plan.add_step(
        "book_flight",
        {
            "passenger_name": "Palak",
            "flight_id": "FL123",
        },
    )

    assert get_next_step(plan, 0).tool_name == "book_flight"
    assert get_next_step(plan, 1) is None
