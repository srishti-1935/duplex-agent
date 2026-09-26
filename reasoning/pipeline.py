from dataclasses import dataclass
from typing import Any, Dict, Optional

from reasoning.intent import extract_intent_and_slots
from reasoning.tool_call import build_tool_call
from reasoning.validator import validate_tool_args
from schemas import Action, ActionType


@dataclass
class PipelineResult:
    action: Action
    intent: Optional[str]
    slots: Dict[str, Any]
    missing_slots: list[str]


def process_text(text: str, revision: int = 1) -> PipelineResult:
    """
    Process user text through the P2 reasoning pipeline.

    Returns either:
    - TOOL_CALL when all required slots are available
    - CLARIFICATION_REQUEST when required information is missing
    """

    result = extract_intent_and_slots(text)

    if result.intent is None:
        action = Action(
            type=ActionType.CLARIFICATION_REQUEST,
            clarification_question="Could you clarify what you'd like me to do?",
            ambiguous_slots=[],
            revision=revision,
        )

        return PipelineResult(
            action=action,
            intent=None,
            slots={},
            missing_slots=[],
        )

    valid, missing, args = validate_tool_args(
        result.intent,
        result.slots,
    )

    if not valid:
        question = (
            f"I need the following information: "
            f"{', '.join(missing)}."
        )

        action = Action(
            type=ActionType.CLARIFICATION_REQUEST,
            clarification_question=question,
            ambiguous_slots=missing,
            revision=revision,
        )

        return PipelineResult(
            action=action,
            intent=result.intent,
            slots=result.slots,
            missing_slots=missing,
        )

    action = build_tool_call(
        result.intent,
        args,
        revision=revision,
    )

    return PipelineResult(
        action=action,
        intent=result.intent,
        slots=args,
        missing_slots=[],
    )
