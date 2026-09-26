"""
Test harness for duplex-agent (P4).

Drives orchestrator.loop.Orchestrator directly with a sequence of timed
Events, captures every Action it emits plus the final StateSnapshot, and
runs a scenario's assertions against that trace.

Deliberately independent of asyncio.Queue's blocking semantics for input:
we call Orchestrator.handle_event() directly so we can inject a "delay
before this event" per-step, which is what lets us build the race-condition
and rapid-double-interruption scenarios the PRD's Day 2 PM stress test
asks for (Section 5).

Usage:
    from frontend.scenarios import SCENARIOS
    from frontend.harness import run_scenario, run_all

    run_all(SCENARIOS)               # prints a summary table
    result = run_scenario(SCENARIOS[0])   # run + inspect one
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from schemas import Event, Action, StateSnapshot
from orchestrator.loop import Orchestrator


# A step is either a single Event fired after `delay` seconds, or a list of
# Events fired concurrently (to simulate two things arriving "at once" —
# e.g. an interruption landing right as a tool result resolves).
Step = tuple[float, Event | list[Event]]

# A check receives the full trace and returns (passed, message).
Check = Callable[["Trace"], tuple[bool, str]]


@dataclass
class Trace:
    """Everything observed while running one scenario."""
    actions: list[Action] = field(default_factory=list)
    action_times: list[float] = field(default_factory=list)  # seconds since scenario start
    final_state: StateSnapshot | None = None
    orchestrator: Orchestrator | None = None


@dataclass
class Scenario:
    name: str
    description: str
    steps: list[Step]
    checks: list[Check]
    # Runs once right after the Orchestrator is constructed, before any
    # steps fire. Lets a scenario seed in-flight state (e.g. a dispatched
    # task_manager entry) that the current stub loop has no event-driven
    # path to reach yet, so we can still test staleness/cancellation logic
    # in isolation ahead of Day 2 integration.
    setup: Callable[[Orchestrator], None] | None = None
    # Marks scenarios that are expected to fail until P2/P3 are wired in
    # (i.e. they exercise a code path the current stub loop can't reach yet).
    # These still run and report, but are called out separately in the
    # summary instead of counting as a broken build.
    known_gap: str | None = None


@dataclass
class ScenarioResult:
    scenario: Scenario
    trace: Trace
    check_results: list[tuple[str, bool, str]]  # (check name, passed, message)

    @property
    def passed(self) -> bool:
        return all(passed for _, passed, _ in self.check_results)


async def _drain(output_queue: asyncio.Queue, trace: Trace, start_time: float) -> None:
    while not output_queue.empty():
        action = output_queue.get_nowait()
        trace.actions.append(action)
        trace.action_times.append(time.monotonic() - start_time)


async def _run_async(scenario: Scenario) -> Trace:
    orchestrator = Orchestrator()
    if scenario.setup:
        scenario.setup(orchestrator)

    output_queue: asyncio.Queue = asyncio.Queue()
    trace = Trace(orchestrator=orchestrator)
    start_time = time.monotonic()

    for delay, step in scenario.steps:
        if delay:
            await asyncio.sleep(delay)

        if isinstance(step, list):
            # concurrent events — race condition simulation
            await asyncio.gather(*(orchestrator.handle_event(e, output_queue) for e in step))
        else:
            await orchestrator.handle_event(step, output_queue)

        await _drain(output_queue, trace, start_time)

    # let any in-flight fake_tool_call()s resolve naturally so we can
    # observe whether their results get discarded (staleness) or acted on
    await asyncio.sleep(0.6)
    await _drain(output_queue, trace, start_time)

    trace.final_state = orchestrator.state
    return trace


def run_scenario(scenario: Scenario) -> ScenarioResult:
    trace = asyncio.run(_run_async(scenario))
    check_results = []
    for check in scenario.checks:
        try:
            passed, message = check(trace)
        except Exception as exc:  # a check itself blowing up is a finding, not a crash
            passed, message = False, f"check raised {type(exc).__name__}: {exc}"
        check_results.append((check.__name__, passed, message))
    return ScenarioResult(scenario=scenario, trace=trace, check_results=check_results)


def run_all(scenarios: list[Scenario]) -> list[ScenarioResult]:
    results = [run_scenario(s) for s in scenarios]
    _print_summary(results)
    return results


def _print_summary(results: list[ScenarioResult]) -> None:
    print("\n" + "=" * 72)
    print(f"{'SCENARIO':<40}{'RESULT':<10}{'NOTE'}")
    print("-" * 72)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        note = "(known gap)" if r.scenario.known_gap else ""
        print(f"{r.scenario.name:<40}{status:<10}{note}")
        for check_name, passed, message in r.check_results:
            if not passed:
                marker = "  ! " if r.scenario.known_gap else "  x "
                print(f"{marker}{check_name}: {message}")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    gaps = sum(1 for r in results if r.scenario.known_gap and not r.passed)
    print("-" * 72)
    print(f"{passed}/{total} scenarios passed"
          f"{f' ({gaps} failures are known integration gaps)' if gaps else ''}")
    print("=" * 72 + "\n")