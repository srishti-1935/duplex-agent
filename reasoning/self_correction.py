from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from reasoning.tool_call import build_tool_call


@dataclass
class CorrectionResult:
    corrected: bool
    slots: Dict[str, Any]
    reason: str


def correct_tool_args(
    tool_name: str,
    slots: Dict[str, Any],
    error: str,
    corrections: Optional[Dict[str, Any]] = None,
) -> CorrectionResult:
    """
    Attempt to correct a failed tool call.

    corrections contains updated slot values supplied by the
    reasoning layer or a later tool result.
    """

    updated_slots = dict(slots)

    if corrections:
        updated_slots.update(corrections)

    try:
        build_tool_call(
            tool_name,
            updated_slots,
        )
    except ValueError as exc:
        return CorrectionResult(
            corrected=False,
            slots=updated_slots,
            reason=str(exc),
        )

    if corrections:
        return CorrectionResult(
            corrected=True,
            slots=updated_slots,
            reason=f"Corrected after tool error: {error}",
        )

    return CorrectionResult(
        corrected=False,
        slots=updated_slots,
        reason=f"Tool call failed: {error}",
    )


def should_retry(
    corrected: bool,
    retry_count: int,
    max_retries: int = 1,
) -> bool:
    """
    Prevent unlimited retries.
    """

    return corrected and retry_count < max_retries
