"""
Core event loop for duplex-agent.
Wires together: task manager (in-flight calls), cancellation/staleness,
and the idempotency ledger.

TODO markers show exactly where P2's classifier + LLM output plug in
once their interface is confirmed.
"""

import asyncio
from schemas import Event, EventType, Action, ActionType, StateSnapshot
from orchestrator.task_manager import TaskManager
from orchestrator.cancellation import handle_cancel_decision, is_result_stale
from orchestrator.ledger import already_dispatched, record_dispatch
from multimodal.speech import wav_to_text_event
from multimodal.vision import png_to_text_event


class Orchestrator:
    def __init__(self):
        self.task_manager = TaskManager()
        self.state = StateSnapshot(revision=0, intent=None, slots={})

    async def handle_event(self, event: Event, output_queue: asyncio.Queue):
        if event.type == EventType.AUDIO_WAV:
            event = wav_to_text_event(event)
            await self._handle_input_turn(event, output_queue)

        elif event.type == EventType.VIDEO_FRAME:
            event = png_to_text_event(event)
            await self._handle_input_turn(event, output_queue)

        elif event.type == EventType.TEXT_CHUNK:
            await self._handle_input_turn(event, output_queue)

        elif event.type == EventType.INTERRUPTION:
            await self._handle_interruption(event, output_queue)

        elif event.type == EventType.TOOL_RESULT:
            await self._handle_tool_result(event, output_queue)

        elif event.type == EventType.TOOL_MANIFEST:
            # TODO: hand off to P3's manifest parser, store schema/read-only flag
            pass

    async def _handle_input_turn(self, event: Event, output_queue: asyncio.Queue):
        # TODO: send event (or P3's processed transcript/description) to P2's LLM
        # for intent detection + slot extraction. Expected to return something like:
        #   {"intent": str, "slots": dict, "tool_name": str|None, "tool_args": dict|None}
        # For now, stub it out so the loop runs end to end.
        parsed = {"intent": "stub_intent", "slots": {}, "tool_name": None, "tool_args": None}

        if parsed["tool_name"] and parsed["tool_args"] is not None:
            await self._dispatch_tool_call(parsed, output_queue)
        else:
            action = Action(type=ActionType.FILLER, filler_text="[stub] processing your request...")
            await output_queue.put(action)

    async def _dispatch_tool_call(self, parsed: dict, output_queue: asyncio.Queue):
        intent = parsed["intent"]
        slots = parsed["slots"]
        tool_name = parsed["tool_name"]

        # TODO: check tool_manifest's read_only flag here — only gate state-modifying calls
        if already_dispatched(intent, slots, tool_name):
            return  # duplicate, silently skip

        call_id = f"call_{self.state.revision}_{tool_name}"

        async def fake_tool_call():
            # TODO: replace with P3's real tool execution wrapper
            await asyncio.sleep(0.5)
            return {"status": "ok"}

        self.task_manager.dispatch(
            call_id, fake_tool_call(), revision=self.state.revision,
            tool_name=tool_name, normalized_slots=slots,
        )
        record_dispatch(intent, slots, tool_name, call_id)

        action = Action(
            type=ActionType.TOOL_CALL, call_id=call_id, tool_name=tool_name,
            tool_args=parsed["tool_args"], revision=self.state.revision,
        )
        await output_queue.put(action)

    async def _handle_interruption(self, event: Event, output_queue: asyncio.Queue):
        # TODO: send event.interruption_text to P2's classifier, expect back
        # one of: "continue" | "patch" | "cancel" | "clarify"
        classification = "clarify"  # stub default — safest fallback per your policy

        if classification == "continue":
            return  # no action

        elif classification == "cancel":
            # TODO: get real call_id(s) to cancel from current in-flight state
            call_id = None
            if call_id:
                handle_cancel_decision(call_id, self.task_manager)
                await output_queue.put(Action(
                    type=ActionType.CANCELLATION, cancelled_call_id=call_id,
                    reason="user cancelled request",
                ))

        elif classification == "patch":
            # TODO: apply patched slot(s) from P2's slot extraction, bump revision
            self.state = StateSnapshot(
                revision=self.state.revision + 1,
                intent=self.state.intent, slots=self.state.slots,
            )
            await output_queue.put(Action(type=ActionType.FILLER, filler_text="I'm updating that."))

        elif classification == "clarify":
            await output_queue.put(Action(
                type=ActionType.CLARIFICATION_REQUEST,
                clarification_question="Could you clarify what you meant?",
            ))

    async def _handle_tool_result(self, event: Event, output_queue: asyncio.Queue):
        if is_result_stale(event.call_id, self.state.revision, self.task_manager):
            return  # discard silently

        # TODO: pass result_payload to P2's LLM for final response generation
        await output_queue.put(Action(
            type=ActionType.FINAL_RESPONSE,
            response_text="[stub] here's your result",
            state_snapshot=self.state,
        ))


async def process_events(input_queue: asyncio.Queue, output_queue: asyncio.Queue):
    orchestrator = Orchestrator()
    while True:
        event: Event = await input_queue.get()
        if event is None:  # sentinel to stop the loop
            input_queue.task_done()
            break
        await orchestrator.handle_event(event, output_queue)
        input_queue.task_done()


async def main():
    input_queue: asyncio.Queue = asyncio.Queue()
    output_queue: asyncio.Queue = asyncio.Queue()

    consumer_task = asyncio.create_task(process_events(input_queue, output_queue))

    # smoke test — remove once P2/P3 feed real events
    await input_queue.put(Event(type=EventType.TEXT_CHUNK, text="book a flight to Mumbai", is_end_of_turn=True))
    await input_queue.put(None)

    await consumer_task

    while not output_queue.empty():
        action = await output_queue.get()
        print(action)


if __name__ == "__main__":
    asyncio.run(main())