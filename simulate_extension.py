"""
Simulates the in-car destination-change extension scenario:
1. User says "navigate to Bangalore" -> search_route dispatched
2. User interrupts mid-route-search: "actually go to Chennai"
3. Old call is cancelled, revision bumps, update_destination dispatched
4. Stale result from the cancelled call (if it arrives late) is discarded
"""

import asyncio
from schemas import StateSnapshot
from orchestrator.task_manager import TaskManager
from orchestrator.cancellation import handle_cancel_decision, is_result_stale
from orchestrator.ledger import already_dispatched, record_dispatch
from extension_tools import search_route, update_destination


async def slow_search_route(destination):
    await asyncio.sleep(2)  # simulate a slow in-flight call
    return search_route(destination)


async def main():
    task_manager = TaskManager()
    state = StateSnapshot(revision=0, intent="navigate", slots={"destination": "Bangalore"})

    # Step 1: dispatch search_route for Bangalore
    call_id_1 = f"call_{state.revision}_search_route"
    if not already_dispatched(state.intent, state.slots, "search_route"):
        task_manager.dispatch(
            call_id_1, slow_search_route("Bangalore"),
            revision=state.revision, tool_name="search_route",
            normalized_slots=state.slots,
        )
        record_dispatch(state.intent, state.slots, "search_route", call_id_1)
        print(f"[dispatched] {call_id_1} for Bangalore, revision={state.revision}")

    # Step 2: interruption arrives — user changes destination before it finishes
    print("[interruption] user says: actually go to Chennai")
    handle_cancel_decision(call_id_1, task_manager)
    print(f"[cancelled] {call_id_1}")

    # Step 3: bump revision, dispatch update_destination for new state
    state = StateSnapshot(revision=state.revision + 1, intent="navigate", slots={"destination": "Chennai"})
    call_id_2 = f"call_{state.revision}_update_destination"
    task_manager.dispatch(
        call_id_2, asyncio.to_thread(update_destination, "ROUTE_BANG", "Chennai"),
        revision=state.revision, tool_name="update_destination",
        normalized_slots=state.slots,
    )
    record_dispatch(state.intent, state.slots, "update_destination", call_id_2)
    print(f"[dispatched] {call_id_2} for Chennai, revision={state.revision}")

    # Step 4: simulate the OLD cancelled call's result arriving late (stale)
    await asyncio.sleep(2.5)
    if is_result_stale(call_id_1, state.revision, task_manager):
        print(f"[discarded] stale result from {call_id_1} (issued at old revision)")
    else:
        print(f"[ERROR] stale result from {call_id_1} was NOT discarded")

    # Let the real update_destination call finish and show it
    result = await task_manager._calls[call_id_2]["task"]
    print(f"[final result] {result}")


if __name__ == "__main__":
    asyncio.run(main())