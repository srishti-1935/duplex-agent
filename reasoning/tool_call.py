from typing import Any, Dict

from schemas import Action, ActionType
from reasoning.validator import validate_tool_args


def build_tool_call(
    tool_name: str,
    slots: Dict[str, Any],
    revision: int = 1,
) -> Action:
    """
    Convert validated reasoning output into the shared TOOL_CALL action.
    """

    valid, missing, args = validate_tool_args(tool_name, slots)

    if not valid:
        raise ValueError(
            f"Cannot build tool call for '{tool_name}'. "
            f"Missing required slots: {missing}"
        )

    return Action(
        type=ActionType.TOOL_CALL,
        tool_name=tool_name,
        tool_args=args,
        revision=revision,
    )
