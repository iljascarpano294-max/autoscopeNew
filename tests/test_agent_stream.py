"""Stage 5 task 3: Agent.reply_stream event production."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.event import (
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
)
from agentscope.message import Msg, TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.tool import ToolBase, ToolChunk, Toolkit


class AddTool(ToolBase):
    name = "add"
    description = "Add two integers."
    input_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["a", "b"],
    }
    is_concurrency_safe = True
    is_read_only = True

    async def call(self, *, a: int, b: int) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _stream_chunks(text_segments: list[str]) -> list[ChatResponse]:
    chunks = [
        ChatResponse(
            content=[TextBlock(text=segment, id="b1")],
            is_last=False,
        )
        for segment in text_segments
    ]
    chunks.append(
        ChatResponse(
            content=[TextBlock(text="".join(text_segments), id="b1")],
            is_last=True,
        ),
    )
    return chunks


def _tool_call_turn(call_id: str) -> list[ChatResponse]:
    return [
        ChatResponse(
            content=[ToolCallBlock(id=call_id, name="add", input='{"a":')],
            is_last=False,
        ),
        ChatResponse(
            content=[ToolCallBlock(id=call_id, name="add", input=" 2, \"b\": 3}")],
            is_last=False,
        ),
        ChatResponse(
            content=[
                ToolCallBlock(
                    id=call_id,
                    name="add",
                    input='{"a": 2, "b": 3}',
                ),
            ],
            is_last=True,
        ),
    ]


def _collect(agent: Agent, *inputs) -> tuple[list, Msg | None]:
    async def run():
        events, final = [], None
        async for item in agent.reply_stream(*inputs):
            if isinstance(item, Msg):
                final = item
            else:
                events.append(item)
        return events, final

    return asyncio.run(run())


def test_reply_stream_event_order() -> None:
    model = FakeChatModel([_stream_chunks(["Hello, ", "world!"])])
    agent = Agent("Friday", "Be concise", model)

    events, final = _collect(agent, UserMsg("Alice", "Hi"))

    types = [event.type for event in events]
    assert types == [
        "REPLY_START",
        "MODEL_CALL_START",
        "TEXT_BLOCK_START",
        "TEXT_BLOCK_DELTA",
        "TEXT_BLOCK_DELTA",
        "TEXT_BLOCK_END",
        "MODEL_CALL_END",
        "REPLY_END",
    ]
    # Deltas carry the incremental segments; the final Msg is separate.
    deltas = [
        event.delta for event in events if isinstance(event, TextBlockDeltaEvent)
    ]
    assert deltas == ["Hello, ", "world!"]
    assert final is not None and final is not events[-1]
    assert final.content[0].text == "Hello, world!"
    assert final.finished_reason == "completed"

    # The context received the assistant message exactly once.
    assert [msg.role for msg in agent.state.context] == ["user", "assistant"]
    assert final is agent.state.context[-1]


def test_reply_stream_tool_round() -> None:
    model = FakeChatModel(
        [
            _tool_call_turn("call-1"),
            _stream_chunks(["The answer is 5"]),
        ],
    )
    agent = Agent("Friday", "Prompt", model, toolkit=Toolkit(tools=[AddTool()]))

    events, final = _collect(agent, UserMsg("Alice", "What is 2 + 3?"))

    types = [event.type for event in events]
    assert types == [
        "REPLY_START",
        "MODEL_CALL_START",
        "TOOL_CALL_START",
        "TOOL_CALL_DELTA",
        "TOOL_CALL_DELTA",
        "TOOL_CALL_END",
        "MODEL_CALL_END",
        "TOOL_RESULT_START",
        "TOOL_RESULT_TEXT_DELTA",
        "TOOL_RESULT_END",
        "MODEL_CALL_START",
        "TEXT_BLOCK_START",
        "TEXT_BLOCK_DELTA",
        "TEXT_BLOCK_END",
        "MODEL_CALL_END",
        "REPLY_END",
    ]
    assert final.get_text_content() == "The answer is 5"
    # The context holds the tool call, its result and the final text in one
    # assistant message, appended once.
    assistant = agent.state.context[-1]
    assert [block.type for block in assistant.content] == [
        "tool_call",
        "tool_result",
        "text",
    ]


def test_reply_reuses_reply_stream_result() -> None:
    model = FakeChatModel([_stream_chunks(["streamed reply"])])
    agent = Agent("Friday", "Prompt", model)
    reply = asyncio.run(agent.reply(UserMsg("Alice", "Hi")))
    assert reply.content[0].text == "streamed reply"
    assert [msg.role for msg in agent.state.context] == ["user", "assistant"]


def test_reply_stream_model_exception_has_no_reply_end() -> None:
    async def run():
        model = FakeChatModel([RuntimeError("model down")])
        agent = Agent("Friday", "Prompt", model)
        events = []
        async for item in agent.reply_stream(UserMsg("Alice", "Hi")):
            if not isinstance(item, Msg):
                events.append(item)
        return events

    with pytest.raises(RuntimeError, match="model down"):
        asyncio.run(run())


def test_reply_stream_early_close_allows_reuse() -> None:
    async def run():
        model = FakeChatModel(
            [
                _stream_chunks(["Hello, ", "world!"]),
                ChatResponse(
                    content=[TextBlock(text="again")],
                    is_last=True,
                ),
            ],
        )
        agent = Agent("Friday", "Prompt", model)
        agen = agent.reply_stream(UserMsg("Alice", "Hi"))
        seen = 0
        async for _ in agen:
            seen += 1
            if seen == 3:
                break
        await agen.aclose()

        # The state is still usable for a fresh reply.
        reply = await agent.reply(UserMsg("Alice", "Hi again"))
        return seen, reply

    seen, reply = asyncio.run(run())
    assert seen == 3
    assert reply.content[0].text == "again"


def test_reply_stream_exceed_max_iters() -> None:
    model = FakeChatModel(
        [[ChatResponse(
            content=[ToolCallBlock(id=f"call-{i}", name="add", input='{"a": 1, "b": 2}')],
            is_last=True,
        )] for i in range(10)],
    )
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[AddTool()]),
        max_iters=2,
    )
    events, final = _collect(agent, UserMsg("Alice", "Keep adding"))

    end_events = [event for event in events if isinstance(event, ReplyEndEvent)]
    assert len(end_events) == 1
    assert end_events[0].finished_reason == "exceed_max_iters"
    assert final is not None
    assert final.finished_reason == "exceed_max_iters"
