ledger = {}

def already_dispatched(intent, normalized_slots, tool_name):
    key = (intent, tuple(sorted(normalized_slots.items())), tool_name)
    return key in ledger

def record_dispatch(intent, normalized_slots, tool_name, call_id):
    key = (intent, tuple(sorted(normalized_slots.items())), tool_name)
    ledger[key] = call_id