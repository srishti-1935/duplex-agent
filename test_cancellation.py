import asyncio

import pytest

from orchestrator.task_manager import TaskManager
from orchestrator.cancellation import (
    handle_cancel_decision,
    is_result_stale,
)


async def fake_call():
    await asyncio.sleep(0.1)
    return "done"


@pytest.mark.asyncio
async def test_cancel_before_result():
    tm = TaskManager()

    tm.dispatch(
        "call1",
        fake_call(),
        revision=1,
        tool_name="search",
        normalized_slots=(),
    )

    handle_cancel_decision("call1", tm)

    await asyncio.sleep(0.2)

    assert is_result_stale(
        "call1",
        incoming_revision=1,
        task_manager=tm,
    ) is False


@pytest.mark.asyncio
async def test_result_after_revision_bump():
    tm = TaskManager()

    tm.dispatch(
        "call1",
        fake_call(),
        revision=1,
        tool_name="search",
        normalized_slots=(),
    )

    assert is_result_stale(
        "call1",
        incoming_revision=2,
        task_manager=tm,
    ) is True