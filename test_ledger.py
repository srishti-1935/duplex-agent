from orchestrator.ledger import already_dispatched, record_dispatch

intent = "book_flight"
slots = {"destination": "Mumbai", "date": "Oct 4"}
tool = "flight_booking_tool"

assert already_dispatched(intent, slots, tool) is False
record_dispatch(intent, slots, tool, call_id="call123")
assert already_dispatched(intent, slots, tool) is True

print("ledger test passed")