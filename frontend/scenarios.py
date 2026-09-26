"""
Scenario suite for the duplex-agent test runner (P4).

IMPORTANT — these are NOT the 9 public scenarios / ~60 hidden scenarios
mentioned in the PRD (Section 5). Those come from the challenge organizers
and should replace/extend this file once available. What's here instead:

  1. Structural smoke tests that pass against today's stub loop and will
     keep being meaningful once P2/P3 are wired in (Day 2 AM).
  2. Targeted tests of logic that's already real (staleness, cancellation)
     even though the event-driven path to reach it doesn't exist yet —
     these use `setup()` to seed state directly, bypassing the stub.
  3. One race-condition scenario per the Day 2 PM stress-test list.

Each scenario marked `known_gap=...` documents a real integration gap in
the current loop, not a bug in this test file. See the printed summary's
"known gap" notes.
"""

from __future__ import annotations

from schemas import Event, EventType, ActionType, StateSnapshot
from orchestrator.loop import Orchestrator
from frontend.harness import Scenario, Trace


# ---------- checks ----------

def produces_at_least_one_action(trace: Trace) -> tuple[bool, str]:
    if trace.actions:
        return True, f"{len(trace.actions)} action(s) emitted"
    return False, "no actions were emitted for this turn"


def no_duplicate_action_ids(trace: Trace) -> tuple[bool, str]:
    ids = [a.action_id for a in trace.actions]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        return False, f"duplicate action_id(s): {dupes}"
    return True, "all action_ids unique"


def no_duplicate_tool_calls(trace: Trace) -> tuple[bool, str]:
    """Safety & Protocol: same (tool_name, call_id) must never be dispatched twice."""
    call_ids = [a.call_id for a in trace.actions if a.type == ActionType.TOOL_CALL]
    dupes = {c for c in call_ids if call_ids.count(c) > 1}
    if dupes:
        return False, f"tool_call dispatched more than once for call_id(s): {dupes}"
    return True, f"{len(call_ids)} tool_call action(s), no duplicates"


def emits_clarification(trace: Trace) -> tuple[bool, str]:
    kinds = [a.type for a in trace.actions]
    if ActionType.CLARIFICATION_REQUEST in kinds:
        return True, "clarification_request emitted"
    return False, f"expected clarification_request, got: {kinds}"


def no_crash_on_concurrent_interruptions(trace: Trace) -> tuple[bool, str]:
    # If we got here at all, handle_event didn't raise for concurrent input.
    # Real assertion: one response per interruption, none dropped.
    n_clarify = sum(1 for a in trace.actions if a.type == ActionType.CLARIFICATION_REQUEST)
    if n_clarify == 2:
        return True, "both concurrent interruptions produced a response"
    return False, f"expected 2 clarification_requests, got {n_clarify} (dropped or merged)"


def stale_result_produces_no_final_response(trace: Trace) -> tuple[bool, str]:
    finals = [a for a in trace.actions if a.type == ActionType.FINAL_RESPONSE]
    if finals:
        return False, f"stale tool_result was acted on: {finals}"
    return True, "stale tool_result correctly discarded, no final_response emitted"


def patch_bumps_revision(trace: Trace) -> tuple[bool, str]:
    if trace.final_state and trace.final_state.revision >= 1:
        return True, f"revision now {trace.final_state.revision}"
    return False, f"expected revision >= 1 after patch, got {trace.final_state}"


def patch_records_a_diff(trace: Trace) -> tuple[bool, str]:
    if trace.final_state and trace.final_state.diff:
        return True, f"diff: {trace.final_state.diff}"
    return False, "patch bumped revision but StateSnapshot.diff is empty — orchestrator isn't recording what changed"


def any_tool_call_dispatched(trace: Trace) -> tuple[bool, str]:
    if any(a.type == ActionType.TOOL_CALL for a in trace.actions):
        return True, "a tool_call action was dispatched"
    return False, "no tool_call action was ever dispatched from a text_chunk event"


# ---------- scenarios ----------

SCENARIOS: list[Scenario] = [

    Scenario(
        name="single_text_turn",
        description="One end-of-turn text_chunk should produce exactly one visible action.",
        steps=[
            (0, Event(type=EventType.TEXT_CHUNK, text="book a flight to Mumbai", is_end_of_turn=True)),
        ],
        checks=[produces_at_least_one_action, no_duplicate_action_ids],
    ),

    Scenario(
        name="text_turn_reaches_tool_dispatch",
        description=(
            "PRD says a booking request should eventually dispatch a tool_call. "
            "Currently _handle_input_turn's `parsed` dict is hardcoded with "
            "tool_name=None, so this path is structurally unreachable until "
            "P2's real intent/slot extraction is wired in."
        ),
        steps=[
            (0, Event(type=EventType.TEXT_CHUNK, text="book a flight to Mumbai", is_end_of_turn=True)),
        ],
        checks=[any_tool_call_dispatched],
        known_gap="orchestrator/loop.py _handle_input_turn: parsed[] is stubbed, tool_name always None",
    ),

    Scenario(
        name="bare_interruption_defaults_to_clarify",
        description="An interruption with no context should hit the safe default (clarify), per the PRD's 'default to clarify on low confidence' policy.",
        steps=[
            (0, Event(type=EventType.INTERRUPTION, interruption_text="wait, actually")),
        ],
        checks=[emits_clarification],
    ),

    Scenario(
        name="rapid_double_interruption",
        description="Two interruptions arriving back-to-back (Day 2 PM stress case) should not crash the loop or drop a response.",
        steps=[
            (0, [
                Event(type=EventType.INTERRUPTION, interruption_text="no wait"),
                Event(type=EventType.INTERRUPTION, interruption_text="actually never mind"),
            ]),
        ],
        checks=[no_crash_on_concurrent_interruptions],
    ),

    Scenario(
        name="patch_bumps_revision_and_records_diff",
        description="A 'patch' classification should bump the revision AND record what changed — the orchestrator currently only does the former.",
        steps=[
            (0, Event(type=EventType.INTERRUPTION, interruption_text="wait, actually the destination is Delhi")),
        ],
        checks=[patch_bumps_revision, patch_records_a_diff],
        known_gap="orchestrator/loop.py _handle_interruption 'patch' branch never populates StateSnapshot.diff; also classification is hardcoded to 'clarify' so this scenario can't even reach the patch branch yet",
    ),

    Scenario(
        name="stale_tool_result_after_revision_bump",
        description=(
            "Seeds a dispatched call at revision 0 directly via TaskManager "
            "(bypassing the stub, since text_chunk can't dispatch real tool "
            "calls yet), bumps state to revision 1, then delivers a "
            "tool_result tagged with the old call_id. It must be discarded."
        ),
        setup=lambda orch: (
            orch.task_manager.dispatch(
                "call_0_flight_booking_tool",
                _fake_slow_call(),
                revision=0, tool_name="flight_booking_tool", normalized_slots={},
            ),
            setattr(orch, "state", StateSnapshot(revision=1, intent="book_flight", slots={})),
        ),
        steps=[
            (0, Event(
                type=EventType.TOOL_RESULT,
                call_id="call_0_flight_booking_tool",
                tool_name="flight_booking_tool",
                result_payload={"status": "ok"},
                success=True,
            )),
        ],
        checks=[stale_result_produces_no_final_response],
    ),
]


async def _fake_slow_call():
    import asyncio
    await asyncio.sleep(0.05)
    return {"status": "ok"}