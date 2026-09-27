from typing import Any, Dict, List, Tuple

from reasoning.tool_schemas import TOOLS


def validate_tool_args(
    tool_name: str,
    slots: Dict[str, Any],
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate extracted slots against the FDB-v3 tool schema.

    Returns:
        valid: whether all required slots are present
        missing: list of missing required slots
        args: filtered arguments containing only schema-defined slots
    """

    if tool_name not in TOOLS:
        return False, ["unknown_tool"], {}

    schema = TOOLS[tool_name]

    required = schema["required"]
    optional = schema["optional"]

    missing = [
        slot
        for slot in required
        if slot not in slots or slots[slot] is None
    ]

    allowed = set(required + optional)

    args = {
        key: value
        for key, value in slots.items()
        if key in allowed and value is not None
    }

    return len(missing) == 0, missing, args
