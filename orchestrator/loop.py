"""
Minimal asyncio skeleton — pass-through only, no real decision logic yet.
Reads Events off input_queue, writes a dummy Action to output_queue.
Real logic (task manager, cancellation, revision tagging, idempotency)
gets layered in after P2/P3/P4 confirm they can import schemas.py cleanly.
"""

import asyncio
from schemas import Event, Action, ActionType


async def process_events(input_queue: asyncio.Queue, output_queue: asyncio.Queue):
    while True:
        event: Event = await input_queue.get()
        if event is None:  # sentinel to stop the loop
            input_queue.task_done()
            break

        # TODO: replace with real dispatch to task manager / classifier / LLM
        dummy_action = Action(
            type=ActionType.FILLER,
            filler_text=f"[stub] received event {event.type}",
        )
        await output_queue.put(dummy_action)
        input_queue.task_done()


async def main():
    input_queue: asyncio.Queue = asyncio.Queue()
    output_queue: asyncio.Queue = asyncio.Queue()

    consumer_task = asyncio.create_task(process_events(input_queue, output_queue))

    # temporary smoke test — remove once P2/P3 are feeding real events
    from schemas import EventType
    await input_queue.put(Event(type=EventType.TEXT_CHUNK, text="hello", is_end_of_turn=True))
    await input_queue.put(None)  # sentinel

    await consumer_task

    while not output_queue.empty():
        action = await output_queue.get()
        print(action)


if __name__ == "__main__":
    asyncio.run(main())