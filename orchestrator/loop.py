import asyncio

from schemas import Event, EventType, Action, ActionType, StateSnapshot, SlotDiff
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

    async def handle_event(self, event, output_queue):
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

    async def _handle_input_turn(self, event, output_queue):
        if not event.text:
            await output_queue.put(
                Action(
                    type=ActionType.CLARIFICATION_REQUEST,
                    clarification_question="Could you clarify what you'd like me to do?",
                    revision=self.state.revision,
                )
            )
            return

        result = process_text(
            event.text,
            revision=self.state.revision,
        )

        self.state = StateSnapshot(
            revision=self.state.revision,
            intent=result.intent,
            slots=result.slots,
        )

        action = result.action

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

        await output_queue.put(action)

    async def _dispatch_tool_call(self, parsed, output_queue):
        intent = parsed["intent"]
        slots = parsed["slots"]
        tool_name = parsed["tool_name"]

        if already_dispatched(
            intent,
            slots,
            tool_name,
        ):
            return

        call_id = f"call_{self.state.revision}_{tool_name}"

        async def fake_tool_call():
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

        await output_queue.put(
            Action(
                type=ActionType.TOOL_CALL,
                call_id=call_id,
                tool_name=tool_name,
                tool_args=parsed["tool_args"],
                revision=self.state.revision,
            )
        )

    async def _handle_interruption(self, event, output_queue):
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
            else:
                await output_queue.put(
                    Action(
                        type=ActionType.CLARIFICATION_REQUEST,
                        clarification_question=(
                            "Could you clarify what you'd like me to cancel?"
                        ),
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

            # Handle partial slot updates from interruptions.
            if not result.slots:
                lower_text = text.lower()

                if "destination is " in lower_text:
                    destination = text.split("destination is ", 1)[1].strip()
                    new_slots["destination"] = destination

            diff = []

            for slot in set(old_slots) | set(new_slots):
                old_value = old_slots.get(slot)
                new_value = new_slots.get(slot)

                if old_value != new_value:
                    diff.append(
                        SlotDiff(
                            slot=slot,
                            old_value=old_value,
                            new_value=new_value,
                        )
                    )

            self.state = StateSnapshot(
                revision=self.state.revision + 1,
                intent=result.intent or self.state.intent,
                slots=new_slots,
                diff=diff,
            )

            await output_queue.put(
                Action(
                    type=ActionType.FILLER,
                    filler_text="I'm updating that.",
                    revision=self.state.revision,
                    state_snapshot=self.state,
                )
            )

        elif classification == "clarify":
            await output_queue.put(
                Action(
                    type=ActionType.CLARIFICATION_REQUEST,
                    clarification_question="Could you clarify what you meant?",
                    revision=self.state.revision,
                )
            )

    @staticmethod
    def _classify_interruption(text):
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

        patch_phrases = [
            "actually the",
            "actually make",
            "actually change",
            "instead make",
            "instead use",
            "change the",
            "change it to",
            "make it",
            "no, the",
            "no, change",
        ]

        if any(phrase in text for phrase in patch_phrases):
            return "patch"

        continue_words = [
            "continue",
            "go ahead",
            "keep going",
        ]

        if any(word in text for word in continue_words):
            return "continue"

        return "clarify"

    async def _handle_tool_result(self, event, output_queue):
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