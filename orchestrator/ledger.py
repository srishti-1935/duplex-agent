"""
Idempotency ledger — prevents the same state-modifying tool call
from being dispatched twice (e.g. if an interruption/retry logic
accidentally tries to re-fire a call that's already in flight or done).

Keyed by (intent, normalized_slots, tool_name).
"""

ledger = {}


def make_key(intent, normalized_slots, tool_name):
    # normalized_slots is a dict — convert to a sorted tuple so it's hashable
    # and consistent regardless of key insertion order
    return (intent, tuple(sorted(normalized_slots.items())), tool_name)


def already_dispatched(intent, normalized_slots, tool_name):
    key = make_key(intent, normalized_slots, tool_name)
    return key in ledger


def record_dispatch(intent, normalized_slots, tool_name, call_id):
    key = make_key(intent, normalized_slots, tool_name)
    ledger[key] = call_id


def get_call_id(intent, normalized_slots, tool_name):
    key = make_key(intent, normalized_slots, tool_name)
    return ledger.get(key)