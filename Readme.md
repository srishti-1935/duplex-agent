# duplex-agent

**Samsung PRISM — Theme 05: Interruptible Real-Time Agents**
Team of 4 · 2-day build window

> Status: skeleton — fill in as P1/P2/P3 land their pieces. Sections marked `TODO` need real content before submission.

## Problem

A voice-native agent, built inside the [LiveKit agents framework](https://github.com/livekit/agents), that:

- **Stays responsive** — spoken feedback within a few hundred ms, no dead air, no false "done" claims
- **Works asynchronously** — tool calls, perception, and reasoning never block the conversation
- **Recovers cleanly** — mid-utterance corrections discard stale intent, update tool args, and never repeat a state-changing action

Evaluated against **[Full-Duplex-Bench v3 (FDB-v3)](https://github.com/DanielLin94144/Full-Duplex-Bench)** — a real, public benchmark ([paper](https://arxiv.org/abs/2604.04847)) of 100 human recordings across 79 scenarios, 12 speakers, 5 annotated disfluency types, and 12 mock tools across 4 domains with chained calls up to 3 levels deep.

Published baselines we're aiming to beat (or at least know where we land against):

| Model | Strict Pass@1 | First response | Tool call latency | Task completion latency |
|---|---|---|---|---|
| GPT-Realtime | 60.0% | 6.36s | 3.89s | 6.89s |
| Gemini Live 3.1 | 54.0% | 3.95s | 2.21s | 4.25s |
| Cascaded (Whisper→GPT-4o→TTS) | — | — | — | 10.12s |

The paper's headline finding — self-correction handling and multi-step tool chains are where every published system loses points — is exactly what our interruption-decision logic is meant to address.

## Architecture

Cascaded template (STT → reasoning/decision → TTS), not a realtime speech API — chosen for 2 days / 4 people because it's easier to insert our own interruption-classification and state-management layer between STT and TTS.

```mermaid
flowchart LR
    A[Microphone audio] --> B[STT]
    B --> C{Interruption classifier}
    C -->|continue| D[No action]
    C -->|patch| E[Patch changed slot,\nkeep in-flight call if still valid]
    C -->|cancel| F[Cancel in-flight call]
    C -->|clarify| G[Ask before acting]
    E --> H[Reasoning / tool selection]
    F --> H
    G --> H
    H --> I[Idempotency ledger\nintent+slots+tool_name]
    I --> J[Tool call\ntagged with state revision]
    J --> K{Result still\ncurrent revision?}
    K -->|yes| L[Update state snapshot + diff]
    K -->|no, stale| M[Discard]
    L --> N[TTS]
```

Carried over from the original design, now living inside the LiveKit agent's reasoning stage:

1. **Interruption classifier** — every interruption/self-correction is one of `continue` / `patch` / `cancel` / `clarify` before any action is taken. Defaults to `clarify` on low confidence (a wrong guess costs Task Completion; asking doesn't).
2. **Versioned state snapshots** — `revision`, `intent`, `slots`, with a recorded diff on every correction.
3. **Idempotency ledger** — keyed by `intent + normalized_slots + tool_name`; never repeats a state-changing tool call.
4. **Revision-tagged tool calls** — a result from a superseded revision is discarded on arrival, regardless of whether cancellation succeeded first.
5. **Cancellation** — wired to whatever concurrency primitive the LiveKit agent runtime uses for in-flight tool calls.

## Repo structure

`TODO` — fill in once P1's LiveKit agent skeleton lands.

## Setup & run

`TODO` — one-command reproduction script goes here once P3 builds it. Must be tested on a machine that isn't the dev machine (P4's job) before submission — 60% of the score is a re-run of this by the organizers.

```
# placeholder — replace with the real reproduction script invocation
git clone <repo>
cd duplex-agent
# ... setup steps ...
# ... run FDB-v3 against the agent ...
```

## Extension use case

`TODO` — one new use case beyond the benchmark's 4 domains, working end-to-end, shown in the demo video (not a slide sketch). Candidates from the PRD: in-car destination change, device troubleshooting with a camera frame, hands-free kitchen assistant. P3 picks and builds one fully rather than splitting effort.

## Benchmark results

`TODO` — our best run's scores, seeds, and config, once P3 has FDB-v3 running end-to-end against the complete agent (Day 2 AM per the timeline).

## Status

| Module | Owner | Status |
|---|---|---|
| P1 — LiveKit agent core + orchestration logic | — | Not started |
| P2 — Reasoning & tool-calling | — | Not started |
| P3 — Benchmark integration & extension | — | Not started |
| P4 — README, video, slides, test runs | Manas | This README skeleton |

## Hard constraints (disqualification risks)

- Never hardcode/memorize/fine-tune on FDB-v3 test items — it's public, they check
- No calling our own servers at evaluation time — all agent logic must live in the submission
- No caching across scenarios — each conversation starts fresh
- Pin seeds and versions so the organizers' re-run matches our logs

## Submission checklist

- [ ] Code repo with this README (architecture diagram, exact setup/run steps, extension clearly marked)
- [ ] One-command reproduction script, verified on a clean machine
- [ ] Our own benchmark run logs (scores, seeds, config)
- [ ] Extension use case, working end-to-end, shown in the video
- [ ] Demo video, 3–5 min, unedited single takes preferred
- [ ] Slide deck, max 8 slides
- [ ] Submitted via the Google Form (one final upload counts)

## Team

**P1 — LiveKit Agent Core + Orchestration Logic:** LiveKit setup, interruption classifier wiring, state/revision system, idempotency ledger, tool-call cancellation.

**P2 — Reasoning & Tool-Calling:** LLM intent detection, slot extraction, tool selection against FDB-v3's 12 mock tools, structured state-snapshot output.

**P3 — Benchmark Integration & Extension:** FDB-v3 setup, baseline run, one-command reproduction script, run logs, the extension use case.

**P4 — README, Video, Slides, Test Runs:** This document, architecture diagram, demo video, slide deck, and independent verification of the reproduction script on a clean machine.