"""
Live trace server for duplex-agent (P4).

Runs a scenario from frontend.scenarios through the real Orchestrator and
broadcasts every Event sent in, every Action emitted out, and every state
change, over a WebSocket — so a judge can watch the agent think in real
time during the demo instead of reading a log afterward.

No changes to orchestrator/loop.py are needed: we pass in a plain
asyncio.Queue subclass (BroadcastQueue) as the output_queue, which does
everything a normal queue does plus pushes a copy to any connected
browser clients.

Usage:
    pip install websockets
    python3 -m frontend.live.server                    # runs the first scenario
    python3 -m frontend.live.server --scenario NAME     # runs a specific one
    python3 -m frontend.live.server --list              # lists scenario names

Then open frontend/live/viewer.html in a browser (just double-click the
file — it only needs the WebSocket, not an HTTP server), and press Enter
in this terminal to fire the scenario.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import websockets

from schemas import Action
from orchestrator.loop import Orchestrator
from frontend.scenarios import SCENARIOS

HOST = "localhost"
PORT = 8765

CONNECTED: set = set()


def _json_default(obj):
    # schemas.py doesn't pin a pydantic major version, so support either.
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)


async def broadcast(message: dict) -> None:
    if not CONNECTED:
        return
    payload = json.dumps(message, default=_json_default)
    await asyncio.gather(*(ws.send(payload) for ws in CONNECTED), return_exceptions=True)


class BroadcastQueue(asyncio.Queue):
    """Drop-in replacement for asyncio.Queue. Every Action put here is
    both queued normally AND streamed live to connected viewers."""

    async def put(self, action: Action) -> None:
        await super().put(action)
        await broadcast({"kind": "action", "data": action})


async def _drain(queue: asyncio.Queue) -> None:
    while not queue.empty():
        queue.get_nowait()


async def run_scenario_live(scenario) -> None:
    orchestrator = Orchestrator()
    if scenario.setup:
        scenario.setup(orchestrator)
    output_queue = BroadcastQueue()

    await broadcast({
        "kind": "scenario_start",
        "name": scenario.name,
        "description": scenario.description,
    })

    for delay, step in scenario.steps:
        if delay:
            await asyncio.sleep(delay)

        events = step if isinstance(step, list) else [step]
        for event in events:
            await broadcast({"kind": "event", "data": event})

        if isinstance(step, list):
            await asyncio.gather(*(orchestrator.handle_event(e, output_queue) for e in events))
        else:
            await orchestrator.handle_event(step, output_queue)

        await broadcast({"kind": "state", "data": orchestrator.state})
        await _drain(output_queue)

    await asyncio.sleep(0.6)  # let any in-flight fake tool calls resolve/discard
    await broadcast({"kind": "scenario_end", "final_state": orchestrator.state})


async def handler(websocket) -> None:
    CONNECTED.add(websocket)
    print(f"viewer connected ({len(CONNECTED)} total)")
    try:
        async for _ in websocket:
            pass  # viewer is read-only for now, we ignore anything it sends
    finally:
        CONNECTED.discard(websocket)
        print(f"viewer disconnected ({len(CONNECTED)} total)")


async def main(scenario_name: str | None) -> None:
    scenario = (
        next((s for s in SCENARIOS if s.name == scenario_name), None)
        if scenario_name else SCENARIOS[0]
    )
    if scenario is None:
        print(f"No scenario named '{scenario_name}'. Use --list to see options.")
        sys.exit(1)

    async with websockets.serve(handler, HOST, PORT):
        print(f"Live trace server running at ws://{HOST}:{PORT}")
        print(f"Open frontend/live/viewer.html in a browser, then press Enter here to run '{scenario.name}'.")
        loop = asyncio.get_event_loop()
        while True:
            await loop.run_in_executor(None, input)
            await run_scenario_live(scenario)
            print("Done. Press Enter to run it again, or Ctrl+C to quit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default=None, help="Scenario name from frontend/scenarios.py")
    parser.add_argument("--list", action="store_true", help="List available scenario names and exit")
    args = parser.parse_args()

    if args.list:
        for s in SCENARIOS:
            gap = f"  [known gap: {s.known_gap}]" if s.known_gap else ""
            print(f"- {s.name}: {s.description}{gap}")
        sys.exit(0)

    try:
        asyncio.run(main(args.scenario))
    except KeyboardInterrupt:
        pass