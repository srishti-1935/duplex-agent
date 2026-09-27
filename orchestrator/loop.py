"""
Core event loop for duplex-agent.

Wires together:
- task manager
- cancellation/staleness
- idempotency ledger
- multimodal preprocessing
- P2 reasoning pipeline
"""

import asyncio

from schemas import Event, EventType, Action, ActionType, StateSnapshot

from orchestrator.task_manager import TaskManager
from orchestrator.cancellation import handle_cancel_decision, is_result_stale
from orchestrator.ledger import already_dispatched, record_dispatch
from orchestrator.manifest_store import store_manifest

from multimodal.speech import wav_to_text_event
from multimodal.vision import png_to_text_event

from reasoning.pipeline import process_text


class Orchestrator:

    def __init__(self):
        self.task_manager = TaskManager()
        self.state = StateSnapshot(
            revision=0,
            intent=None,
            slots={},
        )

    async def handle_event(
        self,
        event: Event,
        output_queue: asyncio.Queue,
    ):
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
            store_manifest(event.manifest)

    async def _handle_input_turn(
        self,
        event: Event,
        output_queue: asyncio.Queue,
    ):
        """
        Send text to the P2 reasoning pipeline.

        The pipeline performs:
        intent detection
        -> slot extraction
        -> argument validation
        -> tool-call construction
        -> clarification if information is missing
        """

        if not event.text:
            await output_queue.put(
                Action(
                    type=ActionType.CLARIFICATION_REQUEST,
                    clarification_question="I didn't receive any text. Could you try again?",
                    ambiguous_slots=[],
                    revision=self.state.revision,
                )
            )
            return

        result = process_text(
            event.text,
            revision=self.state.revision,
        )

        # Update reasoning state.
        self.state = StateSnapshot(
            revision=self.state.revision,
            intent=result.intent,
            slots=result.slots,
        )

        action = result.action

        # If this is a tool call, dispatch it through the
        # existing orchestrator mechanism.
        if action.type == ActionType.TOOL_CALL:
            parsed = {
                "intent": result.intent,
                "slots": result.slots,
                "tool_name": action.tool_name,
                "tool_args": action.tool_args,
            }

            await self._dispatch_tool_call(
                parsed,
                output_queue,
            )
            return

        # Otherwise forward clarification/filler/etc.
        await output_queue.put(action)

    async def _dispatch_tool_call(
        self,
        parsed: dict,
        output_queue: asyncio.Queue,
    ):
        intent = parsed["intent"]
        slots = parsed["slots"]
        tool_name = parsed["tool_name"]

        if already_dispatched(
            intent,
            slots,
            tool_name,
        ):
            return

        call_id = (
            f"call_{self.state.revision}_{tool_name}"
        )

        async def fake_tool_call():
            # Temporary placeholder until P3's
            # real tool execution wrapper is connected.
            await asyncio.sleep(0.5)
            return {"status": "ok"}

        self.task_manager.dispatch(
            call_id,
            fake_tool_call(),
            revision=self.state.revision,
            tool_name=tool_name,
            normalized_slots=slots,
        )

        record_dispatch(
            intent,
            slots,
            tool_name,
            call_id,
        )

        action = Action(
            type=ActionType.TOOL_CALL,
            call_id=call_id,
            tool_name=tool_name,
            tool_args=parsed["tool_args"],
            revision=self.state.revision,
        )

        await output_queue.put(action)

    async def _handle_interruption(
        self,
        event: Event,
        output_queue: asyncio.Queue,
    ):
        """
        Classify an interruption.

        Current P2 classifier is rule-based and returns:
        continue / patch / cancel / clarify
        """

        text = event.interruption_text or ""

        classification = self._classify_interruption(text)

        if classification == "continue":
            return

        elif classification == "cancel":
            call_id = None

            if call_id:
                handle_cancel_decision(
                    call_id,
                    self.task_manager,
                )

                await output_queue.put(
                    Action(
                        type=ActionType.CANCELLATION,
                        cancelled_call_id=call_id,
                        reason="user cancelled request",
                    )
                )

        elif classification == "patch":
            result = process_text(
                text,
                revision=self.state.revision + 1,
            )

            old_slots = dict(self.state.slots)
            new_slots = dict(old_slots)
            new_slots.update(result.slots)

            self.state = StateSnapshot(
                revision=self.state.revision + 1,
                intent=result.intent or self.state.intent,
                slots=new_slots,
            )

            await output_queue.put(
                Action(
                    type=ActionType.FILLER,
                    filler_text="I'm updating that.",
                )
            )

        elif classification == "clarify":
            await output_queue.put(
                Action(
                    type=ActionType.CLARIFICATION_REQUEST,
                    clarification_question=(
                        "Could you clarify what you meant?"
                    ),
                )
            )

    @staticmethod
    def _classify_interruption(text: str) -> str:
        """
        Lightweight interruption classifier.

        This is intentionally conservative until the final
        P2/P3 classifier interface is agreed upon.
        """

        text = text.lower().strip()

        if not text:
            return "clarify"

        cancel_words = [
            "cancel",
            "stop",
            "never mind",
            "nevermind",
            "forget it",
        ]

        if any(word in text for word in cancel_words):
            return "cancel"

        patch_words = [
            "actually",
            "instead",
            "change",
            "make it",
            "no,",
        ]

        if any(word in text for word in patch_words):
            return "patch"

        continue_words = [
            "continue",
            "go ahead",
            "keep going",
        ]

        if any(word in text for word in continue_words):
            return "continue"

        return "clarify"

    async def _handle_tool_result(
        self,
        event: Event,
        output_queue: asyncio.Queue,
    ):
        if is_result_stale(
            event.call_id,
            self.state.revision,
            self.task_manager,
        ):
            return

        await output_queue.put(
            Action(
                type=ActionType.FINAL_RESPONSE,
                response_text="[stub] here's your result",
                state_snapshot=self.state,
            )
        )


async def process_events(
    input_queue: asyncio.Queue,
    output_queue: asyncio.Queue,
):
    orchestrator = Orchestrator()

    while True:
        event: Event = await input_queue.get()

        if event is None:
            input_queue.task_done()
            break

        await orchestrator.handle_event(
            event,
            output_queue,
        )

        input_queue.task_done()


async def main():
    input_queue: asyncio.Queue = asyncio.Queue()
    output_queue: asyncio.Queue = asyncio.Queue()

    consumer_task = asyncio.create_task(
        process_events(
            input_queue,
            output_queue,
        )
    )

    await input_queue.put(
        Event(
            type=EventType.TEXT_CHUNK,
            text="book a flight to Mumbai",
            is_end_of_turn=True,
        )
    )

    await input_queue.put(None)

    await consumer_task

    while not output_queue.empty():
        action = await output_queue.get()
        print(action)


if __name__ == "__main__":
    asyncio.run(main())