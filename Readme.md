# Interruptible Real-Time Agent

**Samsung PRISM — Theme 05: Interruptible Real-Time Agents**
Team of 4 · 2-day build window

## Problem

An agent consumes a stream of timestamped events — text chunks, WAV clips, PNG frames, interruption signals, tool results, tool manifests — over an input queue, and produces actions — fillers, tool calls, cancellations, clarification requests, final responses with state snapshots — over an output queue.

The hard requirements: no duplicate state-changing calls, no acting on stale (superseded) tool results, and no false claims of task completion.

We are **not** doing interruption *detection* from raw audio. Interruption signals arrive as explicit input events; this project is the decision and orchestration logic for what happens after one arrives.

Scoring: Task Completion 40%, Interruption Recovery 35%, Response Latency 15%, Safety & Protocol 10% (see `PRD-interruptible-realtime-agent.md` for the full spec).

## Architecture

Raw `asyncio`, no framework, for full control over cancellation semantics.

```
Event (in) ──► Orchestrator ──► Action (out)
                   │
      ┌────────────┼─────────────┐
      ▼            ▼             ▼
 TaskManager    Ledger      Reasoning layer
 (in-flight     (idempotency (intent/slot
  calls by      by intent+   detection,
  call_id,      slots+tool)  interruption
  revision)                  classifier)
```

Every dispatched tool call is tagged with the state **revision** it was issued under. If a tool result comes back after the state has moved to a newer revision, it's discarded — regardless of whether `Task.cancel()` succeeded in time. This is the core mechanism behind the Interruption Recovery scoring criterion.

Interruptions are classified into exactly one of four types before any action is taken:

| Type | Meaning | Action |
|---|---|---|
| `continue` | Benign aside | No action |
| `patch` | Correction to a slot | Patch only that slot, keep in-flight call running if still valid |
| `cancel` | Request is obsolete | Cancel in-flight call(s) |
| `clarify` | Ambiguous | Ask before acting |

**Default is `clarify` on low confidence** — a wrong guess costs Task Completion; asking for clarification doesn't.

## Repo structure

```
schemas.py                 Shared contract: Event, Action, StateSnapshot, SlotDiff
orchestrator/
  loop.py                  Orchestrator — wires everything together (currently stubbed
                            reasoning/multimodal calls; see Known Gaps below)
  task_manager.py           Tracks in-flight asyncio tasks by call_id / revision
  ledger.py                 Idempotency ledger: (intent, normalized_slots, tool_name) -> blocked if repeated
  cancellation.py            handle_cancel_decision, is_result_stale
reasoning/                  Intent/slot extraction + interruption classifier (P2 — in progress)
multimodal/                 WAV/PNG processors, tool manifest parser (P3 — in progress)
frontend/
  harness.py                 Test harness: drives the orchestrator with timed Event
                              sequences, captures the full Action trace + final state
  scenarios.py                Scenario definitions used by both the harness and the
                              live viewer (see Known Gaps — these are NOT yet the
                              official 9 public scenarios)
  run_tests.py                 CLI: runs all scenarios, prints pass/fail summary
  live/
    server.py                  WebSocket server — runs a scenario live, streams every
                                event/action/state change to the browser in real time
    viewer.html                 Browser page — renders the live stream as a color-coded
                                timeline with a live state/diff panel
test_ledger.py, test_cancellation.py   Unit tests for the modules above
main.py                     Entry point — placeholder until Day 2 integration
```

## Setup

```
git clone https://github.com/srishti-1935/interruptible-real-time-agents.git
cd interruptible-real-time-agents
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
pip install websockets       # only needed for the live trace viewer
```

## Running things

**Sanity-check the orchestrator skeleton on its own:**
```
python -m orchestrator.loop
```
Prints one stubbed filler action if everything's wired correctly.

**Run the scenario test suite:**
```
python -m frontend.run_tests
```
Prints a pass/fail table. Failures marked "known gap" are documented integration gaps (see below), not regressions.

**Run the live trace viewer:**
```
python -m frontend.live.server              # starts the WebSocket server
```
Then open `frontend/live/viewer.html` in a browser, wait for the status pill to say "connected," and press Enter in the terminal to fire the scenario. Use `--scenario NAME` to pick a specific one, or `--list` to see all scenario names.

**Unit tests:**
```
python -m pytest test_ledger.py test_cancellation.py
```

## Status

| Module | Owner | Status |
|---|---|---|
| P1 — Core orchestrator | — | Skeleton complete, runs end to end with stubs |
| P2 — Reasoning & decision layer | — | In progress — intent/slot extraction and the real interruption classifier are not yet wired in |
| P3 — Multimodal & tool layer | — | In progress |
| P4 — Frontend / demo / test runner | Manas | Test harness, scenario suite, live trace viewer, this README |

## Known gaps

These are structural gaps in the current stub loop, surfaced by the test suite — flagged here so they don't get lost before Day 2 integration:

1. **Tool dispatch is currently unreachable.** `orchestrator/loop.py`'s `_handle_input_turn` hardcodes `parsed["tool_name"] = None`, so no text input can currently trigger a real tool call, and the ledger/task_manager dispatch path is untested end-to-end via events (though it is unit-tested directly — see `test_ledger.py`, `test_cancellation.py`, and the harness's `stale_tool_result_after_revision_bump` scenario, which seeds a dispatch manually to work around this).
2. **`patch` doesn't record a diff.** The `patch` branch in `_handle_interruption` bumps `StateSnapshot.revision` but never populates `.diff`, so "patch only the changed slot(s)" isn't observable in the state snapshot yet.
3. **The interruption classifier is hardcoded to always return `clarify`.** This is the correct *default*, but means every interruption currently produces the same response regardless of content — the real four-way classification (rules pass + LLM fallback) is P2's work.
4. **Multimodal event shape is underspecified.** `Event.raw_bytes` vs `Event.file_path` for `audio_wav`/`video_frame` is currently either/or with no stated convention — worth confirming with P3 before building a real test harness for those event types.
5. **Test scenarios are placeholders.** `frontend/scenarios.py` currently holds structural smoke tests and staleness/race-condition checks written to validate the harness itself — not the official 9 public scenarios from the challenge. Those should replace/extend this file once available.

## Team

**P1 — Core Orchestrator:** Event loop, queues, task manager, cancellation wiring, revision tagging, idempotency ledger.

**P2 — Reasoning & Decision Layer:** Slow-path LLM (intent/slot extraction, tool selection, JSON schema), interruption classifier.

**P3 — Multimodal & Tool Layer:** WAV→transcript, PNG→visual description, tool manifest parser, mock tool execution.

**P4 — Frontend / Demo / Test Runner (Manas):** Trace viewer (static trace + live), continuous test runner against the scenario suite, this README.