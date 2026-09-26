"""Stage 7 task 2: model-call budget middleware."""

import asyncio
import json

import pytest

from agentscope.agent import Agent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.middleware import BudgetMiddleware
from agentscope.tool import ToolBase, ToolChunk, Toolkit


class CountingTool(ToolBase):
    name = "count_add"
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

        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="allowed",
        )

    async def call(self, *, a: int, b: int) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


def _tool_call_turn() -> ChatResponse:
    return ChatResponse(
        content=[
            ToolCallBlock(
                id="call-1",
                name="count_add",
                input=json.dumps({"a": 2, "b": 3}),
            ),
        ],
        is_last=True,
    )


def test_budget_stop() -> None:
    # A tool round needs two model calls; a budget of one blocks the second.
    budget = BudgetMiddleware(max_model_calls=1)
    model = FakeChatModel([_tool_call_turn(), _tool_call_turn(), _tool_call_turn()])
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[CountingTool()]),
        middlewares=[budget],
    )

    async def run():
        async for _ in agent.reply_stream(UserMsg("Alice", "add")):
            pass

    with pytest.raises(RuntimeError, match="budget"):
        asyncio.run(run())
    assert len(model.calls) == 1


def test_budget_counters_are_per_agent() -> None:
    budget = BudgetMiddleware(max_model_calls=1)
    first_model = FakeChatModel([_text_response("first ok")])
    first = Agent(
        "Friday",
        "Prompt",
        first_model,
        middlewares=[budget],
    )
    second_model = FakeChatModel([_text_response("second ok")])
    second = Agent(
        "Saturday",
        "Prompt",
        second_model,
        middlewares=[budget],
    )

    first_reply = asyncio.run(first.reply(UserMsg("Alice", "Hi")))
    second_reply = asyncio.run(second.reply(UserMsg("Alice", "Hi")))

    # The same middleware instance keeps per-agent counters, so the second
    # agent is unaffected by the first one's usage.
    assert first_reply.get_text_content() == "first ok"
    assert second_reply.get_text_content() == "second ok"


def test_budget_resets_between_replies() -> None:
    budget = BudgetMiddleware(max_model_calls=1)
    model = FakeChatModel(
        [_text_response("one"), _text_response("two")],
    )
    agent = Agent("Friday", "Prompt", model, middlewares=[budget])

    first = asyncio.run(agent.reply(UserMsg("Alice", "Hi")))
    second = asyncio.run(agent.reply(UserMsg("Alice", "Hi again")))

    # Each fresh reply gets its own budget window.
    assert first.get_text_content() == "one"
    assert second.get_text_content() == "two"
    assert len(model.calls) == 2
