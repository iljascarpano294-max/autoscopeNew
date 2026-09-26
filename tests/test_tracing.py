"""Stage 16 task 1: tracing spans over the middleware hooks."""

import asyncio
import json

from agentscope.agent import Agent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.middleware import TracingMiddleware
from agentscope.middleware._tracing import InMemoryExporter, setup_tracing
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

    async def check_permissions(self, tool_input, context):
        from agentscope.permission import PermissionBehavior, PermissionDecision

        return PermissionDecision(behavior=PermissionBehavior.ALLOW, message="ok")

    async def call(self, *, a: int, b: int) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _tool_call_turn() -> ChatResponse:
    return ChatResponse(
        content=[
            ToolCallBlock(id="call-1", name="add", input=json.dumps({"a": 2, "b": 3})),
        ],
        is_last=True,
    )


def test_trace_tree() -> None:
    exporter = InMemoryExporter()
    setup_tracing(exporter=exporter)

    model = FakeChatModel(
        [
            _tool_call_turn(),
            ChatResponse(content=[TextBlock(text="The answer is 5")], is_last=True),
        ],
    )
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[AddTool()]),
        middlewares=[TracingMiddleware()],
    )
    asyncio.run(agent.reply(UserMsg("Alice", "What is 2 + 3?")))

    spans = exporter.spans
    names = [span.name for span in spans]
    assert names.count("agent.reply") == 1
    assert names.count("model.call") == 2
    assert names.count("tool.call") == 1

    # Parent-child: reply is the root; model/tool spans hang off it.
    reply_span = next(span for span in spans if span.name == "agent.reply")
    assert reply_span.parent_id is None
    children = [span for span in spans if span.parent_id == reply_span.span_id]
    assert {span.name for span in children} == {"model.call", "tool.call"}

    # Every span is closed (an exception path also closes its spans).
    assert all(span.ended for span in spans)
    assert all(span.error is None for span in spans)


def test_failed_model_call_closes_span_with_error() -> None:
    exporter = InMemoryExporter()
    setup_tracing(exporter=exporter)

    model = FakeChatModel([RuntimeError("model down")])
    agent = Agent("Friday", "Prompt", model, middlewares=[TracingMiddleware()])

    async def run():
        async for _ in agent.reply_stream(UserMsg("Alice", "Hi")):
            pass

    import pytest

    with pytest.raises(RuntimeError, match="model down"):
        asyncio.run(run())

    spans = exporter.spans
    model_spans = [span for span in spans if span.name == "model.call"]
    assert len(model_spans) == 1
    assert model_spans[0].ended is True
    assert model_spans[0].error is not None
    assert "model down" in model_spans[0].error
    # The reply span also closed (exception propagated through it).
    reply_spans = [span for span in spans if span.name == "agent.reply"]
    assert reply_spans[0].ended is True
    assert reply_spans[0].error is not None
