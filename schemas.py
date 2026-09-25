"""
Shared interface contract for duplex-agent.
All modules (orchestrator, reasoning, multimodal, frontend) import from here.
Do not change field names/types without a sync — this is the integration contract.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid
import time


# ---------- EVENTS (input queue) ----------

class EventType(str, Enum):
    TEXT_CHUNK = "text_chunk"
    AUDIO_WAV = "audio_wav"
    VIDEO_FRAME = "video_frame"
    INTERRUPTION = "interruption"
    TOOL_RESULT = "tool_result"
    TOOL_MANIFEST = "tool_manifest"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    timestamp: float = Field(default_factory=time.time)

    # text_chunk
    text: Optional[str] = None
    is_end_of_turn: Optional[bool] = None

    # audio_wav / video_frame — raw bytes or a path, keep flexible for now
    raw_bytes: Optional[bytes] = None
    file_path: Optional[str] = None

    # interruption
    interruption_text: Optional[str] = None  # what the user said mid-turn, if known

    # tool_result
    call_id: Optional[str] = None
    tool_name: Optional[str] = None
    result_payload: Optional[dict[str, Any]] = None
    success: Optional[bool] = None

    # tool_manifest
    manifest: Optional[dict[str, Any]] = None  # {name, input_schema, read_only, required_args}

    class Config:
        arbitrary_types_allowed = True


# ---------- ACTIONS (output queue) ----------

class ActionType(str, Enum):
    FILLER = "filler"
    TOOL_CALL = "tool_call"
    CANCELLATION = "cancellation"
    CLARIFICATION_REQUEST = "clarification_request"
    FINAL_RESPONSE = "final_response"


class Action(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ActionType
    timestamp: float = Field(default_factory=time.time)

    # filler
    filler_text: Optional[str] = None

    # tool_call
    call_id: Optional[str] = None          # required when type == TOOL_CALL
    tool_name: Optional[str] = None
    tool_args: Optional[dict[str, Any]] = None
    revision: Optional[int] = None         # revision this call was issued under

    # cancellation
    cancelled_call_id: Optional[str] = None
    reason: Optional[str] = None

    # clarification_request
    clarification_question: Optional[str] = None
    ambiguous_slots: Optional[list[str]] = None

    # final_response
    response_text: Optional[str] = None
    state_snapshot: Optional["StateSnapshot"] = None


# ---------- STATE ----------

class SlotDiff(BaseModel):
    slot: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None


class StateSnapshot(BaseModel):
    revision: int
    intent: Optional[str] = None
    slots: dict[str, Any] = Field(default_factory=dict)
    diff: list[SlotDiff] = Field(default_factory=list)  # what changed vs previous revision


Action.model_rebuild()