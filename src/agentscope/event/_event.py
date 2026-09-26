# -*- coding: utf-8 -*-
"""Event types for agent execution."""
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, TypeAlias

from pydantic import BaseModel, Field, ConfigDict

from .._utils._common import _generate_id
from ..message import (
    ToolCallBlock,
    ToolResultState,
)
from ..permission import PermissionRule
from ..types import (
    ReplyFinishedReason,
    ErrorInfo,
)
from ..model import FinishedReason


class EventType(StrEnum):
    """Event type enumeration."""

    REPLY_START = "REPLY_START"
    REPLY_END = "REPLY_END"

    MODEL_CALL_START = "MODEL_CALL_START"
    MODEL_CALL_END = "MODEL_CALL_END"

    TEXT_BLOCK_START = "TEXT_BLOCK_START"
    TEXT_BLOCK_DELTA = "TEXT_BLOCK_DELTA"
    TEXT_BLOCK_END = "TEXT_BLOCK_END"

    DATA_BLOCK_START = "DATA_BLOCK_START"
    DATA_BLOCK_DELTA = "DATA_BLOCK_DELTA"
    DATA_BLOCK_END = "DATA_BLOCK_END"

    THINKING_BLOCK_START = "THINKING_BLOCK_START"
    THINKING_BLOCK_DELTA = "THINKING_BLOCK_DELTA"
    THINKING_BLOCK_END = "THINKING_BLOCK_END"

    HINT_BLOCK = "HINT_BLOCK"

    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_DELTA = "TOOL_CALL_DELTA"
    TOOL_CALL_END = "TOOL_CALL_END"

    TOOL_RESULT_START = "TOOL_RESULT_START"
    TOOL_RESULT_TEXT_DELTA = "TOOL_RESULT_TEXT_DELTA"
    TOOL_RESULT_DATA_DELTA = "TOOL_RESULT_DATA_DELTA"
    TOOL_RESULT_END = "TOOL_RESULT_END"

    EXCEED_MAX_ITERS = "EXCEED_MAX_ITERS"

    REQUIRE_USER_CONFIRM = "REQUIRE_USER_CONFIRM"
    REQUIRE_EXTERNAL_EXECUTION = "REQUIRE_EXTERNAL_EXECUTION"

    USER_CONFIRM_RESULT = "USER_CONFIRM_RESULT"
    USER_INTERRUPT = "USER_INTERRUPT"
    EXTERNAL_EXECUTION_RESULT = "EXTERNAL_EXECUTION_RESULT"

    CUSTOM = "CUSTOM"


class EventBase(BaseModel):
    """Base event class."""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=_generate_id)
    """Unique event identifier."""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    """ISO 8601 timestamp of when the event was created."""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Optional metadata attached to the event."""


class ReplyStartEvent(EventBase):
    """Reply start event."""

    type: Literal[EventType.REPLY_START] = EventType.REPLY_START
    """Event type."""
    reply_id: str
    """ID of the reply message produced by this reply."""
    name: str
    """Name of the agent."""
    role: Literal["user", "assistant", "system"] = "assistant"
    """Role of the agent."""


class ReplyEndEvent(EventBase):
    """Reply end event."""

    type: Literal[EventType.REPLY_END] = EventType.REPLY_END
    """Event type."""
    reply_id: str
    """ID of the reply message produced by this reply."""
    finished_reason: ReplyFinishedReason = ReplyFinishedReason.COMPLETED
    """The finished reason of this reply."""
    error: ErrorInfo | None = None
    """Structured error info, populated only when
    ``finished_reason == ReplyFinishedReason.ERROR``."""


class ModelCallStartEvent(EventBase):
    """Model call start event."""

    type: Literal[EventType.MODEL_CALL_START] = EventType.MODEL_CALL_START
    """Event type."""
    reply_id: str
    """ID of the reply message this model call belongs to."""
    model_name: str
    """Name of the model being called."""


class ModelCallEndEvent(EventBase):
    """Model call end event."""

    type: Literal[EventType.MODEL_CALL_END] = EventType.MODEL_CALL_END
    """Event type."""
    reply_id: str
    """ID of the reply message this model call belongs to."""
    input_tokens: int
    """Number of input tokens consumed."""
    output_tokens: int
    """Number of output tokens generated."""
    cache_input_tokens: int = 0
    """Number of input tokens read from the prompt cache."""
    cache_creation_input_tokens: int = 0
    """Number of input tokens used to create the prompt cache."""
    finished_reason: FinishedReason = Field(
        default=FinishedReason.COMPLETED,
    )
    """The finished reason of this model call."""


class TextBlockStartEvent(EventBase):
    """Text block start event."""

    type: Literal[EventType.TEXT_BLOCK_START] = EventType.TEXT_BLOCK_START
    """Event type."""
    reply_id: str
    """ID of the reply message this block belongs to."""
    block_id: str
    """Unique identifier of the text block."""


class TextBlockDeltaEvent(EventBase):
    """Text block delta event."""

    type: Literal[EventType.TEXT_BLOCK_DELTA] = EventType.TEXT_BLOCK_DELTA
    """Event type."""
    reply_id: str
    """ID of the reply message this block belongs to."""
    block_id: str
    """Unique identifier of the text block."""
    delta: str
    """Incremental text content."""


class TextBlockEndEvent(EventBase):
    """Text block end event."""

    type: Literal[EventType.TEXT_BLOCK_END] = EventType.TEXT_BLOCK_END
    """Event type."""
    reply_id: str
    """ID of the reply message this block belongs to."""
    block_id: str
    """Unique identifier of the text block."""
    text: str | None = None
    """The block's final text, when it is not the concatenation of the
    deltas: a voice reply cut short is truncated to what the user heard."""


class ToolCallStartEvent(EventBase):
    """Tool call start event."""

    type: Literal[EventType.TOOL_CALL_START] = EventType.TOOL_CALL_START
    """Event type."""
    reply_id: str
    """ID of the reply message this tool call belongs to."""
    tool_call_id: str
    """Unique identifier of the tool call."""
    tool_call_name: str
    """Name of the tool being called."""


class ToolCallDeltaEvent(EventBase):
    """Tool call delta event."""

    type: Literal[EventType.TOOL_CALL_DELTA] = EventType.TOOL_CALL_DELTA
    """Event type."""
    reply_id: str
    """ID of the reply message this tool call belongs to."""
    tool_call_id: str
    """Unique identifier of the tool call."""
    delta: str
    """Incremental tool call arguments (JSON fragment)."""


class ToolCallEndEvent(EventBase):
    """Tool call end event."""

    type: Literal[EventType.TOOL_CALL_END] = EventType.TOOL_CALL_END
    """Event type."""
    reply_id: str
    """ID of the reply message this tool call belongs to."""
    tool_call_id: str
    """Unique identifier of the tool call."""


class ToolResultStartEvent(EventBase):
    """Tool result start event."""

    type: Literal[EventType.TOOL_RESULT_START] = EventType.TOOL_RESULT_START
    """Event type."""
    reply_id: str
    """ID of the reply message this tool result belongs to."""
    tool_call_id: str
    """ID of the corresponding tool call."""
    tool_call_name: str
    """Name of the tool that was called."""


class ToolResultTextDeltaEvent(EventBase):
    """Tool result text delta event."""

    type: Literal[
        EventType.TOOL_RESULT_TEXT_DELTA
    ] = EventType.TOOL_RESULT_TEXT_DELTA
    """Event type."""
    reply_id: str
    """ID of the reply message this tool result belongs to."""
    tool_call_id: str
    """ID of the corresponding tool call."""
    delta: str
    """Incremental text content of the tool result."""


class ToolResultEndEvent(EventBase):
    """Tool result end event."""

    model_config = ConfigDict(use_enum_values=True)

    type: Literal[EventType.TOOL_RESULT_END] = EventType.TOOL_RESULT_END
    """Event type."""
    reply_id: str
    """ID of the reply message this tool result belongs to."""
    tool_call_id: str
    """ID of the corresponding tool call."""
    state: ToolResultState
    """Final execution state of the tool call."""
    metadata: dict[str, Any] = Field(default_factory=dict)
    """Optional metadata attached to the tool result event."""


class RequireUserConfirmEvent(EventBase):
    """Require user confirm event."""

    type: Literal[EventType.REQUIRE_USER_CONFIRM] = EventType.REQUIRE_USER_CONFIRM
    """Event type."""
    reply_id: str
    """ID of the reply message associated with this run."""
    tool_calls: List[ToolCallBlock]
    """Tool calls pending user confirmation."""


class ConfirmResult(BaseModel):
    """Confirm result for a tool call."""

    confirmed: bool
    """Whether the user confirmed the tool call."""
    tool_call: ToolCallBlock
    """The tool call that was confirmed or rejected."""
    rules: list[PermissionRule] | None = None
    """The allowed permission rules for this tool call. This field is only
    applicable when ``confirmed`` is True."""


class UserConfirmResultEvent(EventBase):
    """User confirm result event."""

    type: Literal[EventType.USER_CONFIRM_RESULT] = EventType.USER_CONFIRM_RESULT
    """Event type."""
    reply_id: str
    """ID of the reply message associated with this run."""
    confirm_results: list[ConfirmResult]
    """Confirmation results for each pending tool call."""


class UserInterruptEvent(EventBase):
    """User-initiated interrupt targeting a parked reply.

    Delivered to :meth:`Agent.reply_stream` (or :meth:`Agent.reply`) to
    abort a reply that is currently waiting on user confirmation. On
    receipt, the agent closes every pending tool call with an interrupted
    tool result and ends the reply with ``INTERRUPTED``.
    """

    type: Literal[EventType.USER_INTERRUPT] = EventType.USER_INTERRUPT
    """Event type."""
    reply_id: str
    """ID of the reply message this interrupt targets."""


AgentEvent: TypeAlias = (
    ReplyStartEvent
    | ReplyEndEvent
    | ModelCallStartEvent
    | ModelCallEndEvent
    | TextBlockStartEvent
    | TextBlockDeltaEvent
    | TextBlockEndEvent
    | ToolCallStartEvent
    | ToolCallDeltaEvent
    | ToolCallEndEvent
    | ToolResultStartEvent
    | ToolResultTextDeltaEvent
    | ToolResultEndEvent
    | RequireUserConfirmEvent
    | UserConfirmResultEvent
    | UserInterruptEvent
)
