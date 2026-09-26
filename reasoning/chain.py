from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from reasoning.tool_call import build_tool_call


@dataclass
class ToolStep:
    tool_name: str
    slots: Dict[str, Any]
    revision: int


@dataclass
class ChainPlan:
    steps: List[ToolStep] = field(default_factory=list)

    def add_step(
        self,
        tool_name: str,
        slots: Dict[str, Any],
    ) -> ToolStep:
        revision = len(self.steps) + 1

        # Validate the tool call before adding it to the chain.
        build_tool_call(
            tool_name,
            slots,
            revision=revision,
        )

        step = ToolStep(
            tool_name=tool_name,
            slots=slots,
            revision=revision,
        )

        self.steps.append(step)
        return step


def apply_tool_result(
    slots: Dict[str, Any],
    result: Dict[str, Any],
    mappings: Dict[str, str],
) -> Dict[str, Any]:
    """
    Copy values from a tool result into slots needed by
    a later tool call.

    Example:
        result = {"address": "SRM KTR"}
        mappings = {"address": "origin_address"}

    produces:
        {"origin_address": "SRM KTR"}
    """

    updated = dict(slots)

    for result_key, slot_name in mappings.items():
        if result_key in result:
            updated[slot_name] = result[result_key]

    return updated


def get_next_step(
    plan: ChainPlan,
    current_index: int,
) -> Optional[ToolStep]:
    """
    Return the next tool step in the chain.
    """
    next_index = current_index + 1

    if next_index >= len(plan.steps):
        return None

    return plan.steps[next_index]
