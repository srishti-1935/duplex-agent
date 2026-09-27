"""
Stores parsed tool manifests so the orchestrator can look up
input schemas / required args before dispatching a tool call.

No read_only/state-modifying distinction is tracked here — every
tool call goes through the same idempotency ledger regardless.
"""

manifests = {}


def store_manifest(manifest: dict):
    name = manifest.get("name")
    if name:
        manifests[name] = manifest


def get_manifest(tool_name: str):
    return manifests.get(tool_name)