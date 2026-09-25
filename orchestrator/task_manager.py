# orchestrator/task_manager.py
import asyncio

class TaskManager:
    def __init__(self):
        self._calls = {}  # call_id -> {"task": Task, "revision": int, "tool_name": str, "slots": tuple}

    def dispatch(self, call_id, coro, revision, tool_name, normalized_slots):
        task = asyncio.create_task(coro)
        self._calls[call_id] = {
            "task": task, "revision": revision,
            "tool_name": tool_name, "slots": normalized_slots,
        }
        return task

    def cancel(self, call_id):
        entry = self._calls.get(call_id)
        if entry:
            entry["task"].cancel()

    def get_revision(self, call_id):
        entry = self._calls.get(call_id)
        return entry["revision"] if entry else None