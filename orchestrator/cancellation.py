def handle_cancel_decision(call_id, task_manager):
    """
    Called when the interruption classifier returns 'cancel'.
    Fires .cancel() immediately — doesn't wait to check if it worked.
    """
    task_manager.cancel(call_id)


def is_result_stale(call_id, incoming_revision, task_manager):
    """
    Called whenever a tool_result Event arrives on the input queue.
    Returns True if this result should be discarded.
    """
    issued_revision = task_manager.get_revision(call_id)
    if issued_revision is None:
        # we have no record of this call_id — treat as stale/unknown, discard
        return True
    return incoming_revision != issued_revision