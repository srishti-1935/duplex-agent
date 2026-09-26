"""
Entry point: python -m frontend.run_tests

Runs the full scenario suite against the current orchestrator and prints
a pass/fail summary, calling out known integration gaps separately from
real regressions. Intended to be run continuously through Day 1/2 as
P1/P2/P3 land real code behind the stubs.
"""

from frontend.scenarios import SCENARIOS
from frontend.harness import run_all

if __name__ == "__main__":
    run_all(SCENARIOS)