"""Stage 5 task 4: console print_stream renders events without repeats."""

import asyncio
import io

from agentscope.agent import Agent
from agentscope.console import print_stream
from agentscope.event import (
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
)
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel

REPLY_ID = "reply-1"


def _reply_stream_events() -> list:
    return [
        ReplyStartEvent(reply_id=REPLY_ID, name="Friday"),
        ModelCallStartEvent(reply_id=REPLY_ID, model_name="fake"),
        TextBlockStartEvent(reply_id=REPLY_ID, block_id="b1"),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="Hello, "),
        TextBlockDeltaEvent(reply_id=REPLY_ID, block_id="b1", delta="world!"),
        TextBlockEndEvent(reply_id=REPLY_ID, block_id="b1"),
        ModelCallEndEvent(reply_id=REPLY_ID, input_tokens=1, output_tokens=1),
        ReplyEndEvent(reply_id=REPLY_ID),
    ]


def test_console_stream_prints_each_delta_once() -> None:
    buffer = io.StringIO()
    print_stream(_reply_stream_events(), file=buffer)
    output = buffer.getvalue()

    # Each delta is printed exactly once, concatenated in order; the reply
    # is never printed twice and no agent internals are touched.
    assert output == "[Friday] Hello, world!\n"


def test_console_stream_renders_live_agent_reply() -> None:
    async def run():
        model = FakeChatModel(
            [ChatResponse(content=[TextBlock(text=" streamed")], is_last=True)],
        )
        agent = Agent("Friday", "Prompt", model)
        buffer = io.StringIO()
        async for item in agent.reply_stream(UserMsg("Alice", "Hi")):
            print_stream([item], file=buffer)
        return buffer.getvalue()

    output = asyncio.run(run())
    assert " streamed" in output
    # The reply message at the end of the stream must not duplicate the text
    # that the deltas already printed.
    assert output.count(" streamed") == 1
