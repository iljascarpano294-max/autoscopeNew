"""Stage 5 task 1: event models and event_to_message aggregation."""

import pytest

from agentscope.event import (
    EventType,
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
    event_to_message,
)
from agentscope.types import ReplyFinishedReason

REPLY_ID = "reply-1"


def _text_events() -> list:
    return [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        TextBlockStartEvent(reply_id=REPLY_ID, block_id="b1"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="Hello, "),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="world!"),
        TextBlockEndEvent(reply_id=REPLY_ID, block_id="b1"),
        ReplyEndEvent(
            reply_id=REPLY_ID,
            finished_reason=ReplyFinishedReason.COMPLETED,
        ),
    ]


def test_event_type_discriminators() -> None:
    assert ReplyStartEvent(reply_id=REPLY_ID, name="Friday").type == EventType.REPLY_START
    delta = TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="x")
    assert delta.type == EventType.TEXT_BLOCK_DELTA
    assert delta.id and delta.created_at


def test_event_order_and_merge() -> None:
    msg = event_to_message(_text_events())
    assert msg.id == REPLY_ID
    assert msg.name == "Friday"
    assert len(msg.content) == 1
    assert msg.content[0].text == "Hello, world!"
    assert msg.content[0].finished_at is not None
    assert msg.finished_reason == ReplyFinishedReason.COMPLETED
    assert msg.finished_at is not None


def test_empty_delta_produces_no_ghost_text() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        TextBlockStartEvent(reply_id=REPLY_ID, block_id="b1"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta=""),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="real"),
        TextBlockEndEvent(reply_id=REPLY_ID, block_id="b1"),
        ReplyEndEvent(reply_id=REPLY_ID),
    ]
    msg = event_to_message(events)
    assert [block.text for block in msg.content] == ["real"]


def test_delta_before_start_is_an_error() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="x"),
    ]
    with pytest.raises(ValueError, match="before"):
        event_to_message(events)


def test_unknown_block_id_is_an_error() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        TextBlockStartEvent(reply_id=REPLY_ID, block_id="b1"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="other", delta="x"),
    ]
    with pytest.raises(ValueError, match="other"):
        event_to_message(events)


def test_duplicate_reply_end_is_an_error() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        ReplyEndEvent(reply_id=REPLY_ID),
        ReplyEndEvent(reply_id=REPLY_ID),
    ]
    with pytest.raises(ValueError, match="already"):
        event_to_message(events)


def test_reply_id_mismatch_is_an_error() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        TextBlockStartEvent(reply_id="reply-2", block_id="b1"),
    ]
    with pytest.raises(ValueError, match="reply_id"):
        event_to_message(events)


def test_first_event_must_be_reply_start() -> None:
    with pytest.raises(ValueError, match="ReplyStartEvent"):
        event_to_message([TextBlockStartEvent(reply_id=REPLY_ID, block_id="b1")])
    with pytest.raises(ValueError, match="ReplyStartEvent"):
        event_to_message([])


def test_model_call_end_accumulates_usage() -> None:
    events = [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        ModelCallStartEvent(reply_id=REPLY_ID, model_name="fake"),
        ModelCallEndEvent(
            reply_id=REPLY_ID,
            input_tokens=10,
            output_tokens=5,
        ),
        ModelCallEndEvent(
            reply_id=REPLY_ID,
            input_tokens=3,
            output_tokens=2,
        ),
        ReplyEndEvent(reply_id=REPLY_ID),
    ]
    msg = event_to_message(events)
    assert msg.usage.input_tokens == 13
    assert msg.usage.output_tokens == 7
