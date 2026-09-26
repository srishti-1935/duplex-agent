from reasoning.tool_schemas import TOOLS


def test_all_tools_exist():
    assert len(TOOLS) == 12


def test_search_flights_schema():
    tool = TOOLS["search_flights"]

    assert tool["required"] == ["destination", "date"]


def test_book_flight_optional_id():
    tool = TOOLS["book_flight"]

    assert "passenger_name" in tool["required"]
    assert "flight_id" in tool["optional"]


def test_commute_optional_mode():
    tool = TOOLS["calculate_commute"]

    assert "origin_address" in tool["required"]
    assert "destination_address" in tool["required"]
    assert "mode" in tool["optional"]