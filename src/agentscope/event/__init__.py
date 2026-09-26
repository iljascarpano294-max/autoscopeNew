# -*- coding: utf-8 -*-
"""The event module of agentscope."""

from ..message import Msg, TextBlock, Usage
from ..types import ReplyFinishedReason
from ._event import (
    EventType,
    EventBase,
    ReplyStartEvent,
    ReplyEndEvent,
    ModelCallStartEvent,
    ModelCallEndEvent,
    TextBlockStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
    ToolResultEndEvent,
    RequireUserConfirmEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
    ConfirmResult,
    CustomEvent,
    AgentEvent,
)


def event_to_message(events: list[AgentEvent]) -> Msg:
    """Aggregate one reply's event stream into its final assistant message.

    A strict stage-5 state machine: the stream must start with a
    ReplyStartEvent, every reply-scoped event must carry the same reply_id,
    block deltas must follow their start event, and the reply may end only
    once. The reference ``Msg.append_event`` skips inconsistent events with a
    warning instead; here the plan calls for explicit errors so that broken
    streams fail loudly.

    Args:
        events (`list[AgentEvent]`):
            The ordered event stream of one reply.

    Returns:
        `Msg`:
            The assistant message merged from the stream, with usage
            accumulated across ModelCallEndEvent and finished metadata
            stamped by ReplyEndEvent.
    """
    if not events or not isinstance(events[0], ReplyStartEvent):
        raise ValueError(
            "The event stream must start with a ReplyStartEvent, got "
            f"{events[0].__class__.__name__ if events else None}.",
        )

    reply_id = events[0].reply_id
    name = events[0].name
    blocks: list[TextBlock] = []
    open_blocks: dict[str, TextBlock] = {}
    input_tokens = output_tokens = 0
    cache_input_tokens = cache_creation_input_tokens = 0
    has_usage = False
    finished_at: str | None = None
    finished_reason = ReplyFinishedReason.COMPLETED

    for event in events[1:]:
        if event.reply_id != reply_id:
            raise ValueError(
                f"Event {event.__class__.__name__} carries reply_id "
                f"{event.reply_id!r}, which does not match the stream's "
                f"reply_id {reply_id!r}.",
            )

        if isinstance(event, TextBlockStartEvent):
            if event.block_id in open_blocks:
                raise ValueError(
                    f"TextBlock {event.block_id!r} is started twice.",
                )
            block = TextBlock(id=event.block_id, text="")
            blocks.append(block)
            open_blocks[event.block_id] = block

        elif isinstance(event, TextBlockDeltaEvent):
            block = open_blocks.get(event.block_id)
            if block is None:
                raise ValueError(
                    f"TextBlockDeltaEvent for block {event.block_id!r} "
                    f"arrived before its TextBlockStartEvent.",
                )
            block.text += event.delta

        elif isinstance(event, TextBlockEndEvent):
            block = open_blocks.pop(event.block_id, None)
            if block is None:
                raise ValueError(
                    f"TextBlockEndEvent for unknown block "
                    f"{event.block_id!r} arrived.",
                )
            if event.text is not None:
                block.text = event.text
            block.finished_at = event.created_at

        elif isinstance(event, ModelCallEndEvent):
            input_tokens += event.input_tokens
            output_tokens += event.output_tokens
            cache_input_tokens += event.cache_input_tokens
            cache_creation_input_tokens += event.cache_creation_input_tokens
            has_usage = True

        elif isinstance(event, ReplyEndEvent):
            if finished_at is not None:
                raise ValueError(
                    "The reply has already finished; a second ReplyEndEvent "
                    "is not allowed.",
                )
            finished_at = event.created_at
            finished_reason = ReplyFinishedReason(event.finished_reason)

        # ModelCallStartEvent and tool-level events carry no message state.

    return Msg(
        id=reply_id,
        role="assistant",
        name=name,
        content=blocks,
        usage=Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_input_tokens=cache_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
        ) if has_usage else None,
        finished_at=finished_at,
        finished_reason=str(finished_reason) if finished_at else None,
    )


__all__ = [
    "EventType",
    "EventBase",
    "ReplyStartEvent",
    "ReplyFinishedReason",
    "ReplyEndEvent",
    "ModelCallStartEvent",
    "ModelCallEndEvent",
    "TextBlockStartEvent",
    "TextBlockDeltaEvent",
    "TextBlockEndEvent",
    "ToolCallStartEvent",
    "ToolCallDeltaEvent",
    "ToolCallEndEvent",
    "ToolResultStartEvent",
    "ToolResultTextDeltaEvent",
    "ToolResultEndEvent",
    "RequireUserConfirmEvent",
    "UserConfirmResultEvent",
    "UserInterruptEvent",
    "ConfirmResult",
    "CustomEvent",
    "AgentEvent",
    "event_to_message",
]
