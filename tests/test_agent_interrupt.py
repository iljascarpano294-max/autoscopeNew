"""Stage 6 task 4: interrupt cleanup and state serialization round-trip."""

import asyncio
import json

import pytest

from agentscope.agent import Agent
from agentscope.event import (
    RequireUserConfirmEvent,
    ReplyEndEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
)
from agentscope.message import TextBlock, ToolCallBlock, ToolResultState, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionEngine,
    PermissionMode,
)
from agentscope.state import AgentState
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
    is_read_only = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.executions = 0

    async def check_permissions(self, tool_input, context):
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="defer to the engine",
        )

    async def call(self, *, a: int, b: int) -> ToolChunk:
        self.executions += 1
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _agent(model: FakeChatModel, tool: CountingTool) -> Agent:
    return Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[tool]),
        permission_engine=PermissionEngine(
            PermissionContext(mode=PermissionMode.DEFAULT),
        ),
    )


def _tool_call_turn(call_id: str) -> ChatResponse:
    return ChatResponse(
        content=[
            ToolCallBlock(
                id=call_id,
                name="count_add",
                input=json.dumps({"a": 2, "b": 3}),
            ),
        ],
        is_last=True,
    )


def _park_agent_on_confirmation(tool: CountingTool) -> Agent:
    model = FakeChatModel([_tool_call_turn("call-1")])
    agent = _agent(model, tool)
    asyncio.run(_consume_once(agent))
    return agent


async def _consume_once(agent: Agent):
    async for _ in agent.reply_stream(UserMsg("Alice", "add")):
        pass


def test_interrupt_closes_pending_calls_without_execution() -> None:
    tool = CountingTool()
    agent = _park_agent_on_confirmation(tool)
    assert tool.executions == 0

    async def run():
        events, final = [], None
        async for item in agent.reply_stream(
            UserInterruptEvent(reply_id=agent.state.reply_id),
        ):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    events, final = asyncio.run(run())

    # The tool never ran and the pending call got an explainable state.
    assert tool.executions == 0
    ends = [e for e in events if isinstance(e, ReplyEndEvent)]
    assert len(ends) == 1
    assert ends[0].finished_reason == "interrupted"
    result = agent.state.context[-1].get_content_blocks("tool_result")[0]
    assert result.state == ToolResultState.INTERRUPTED
    assert agent.state.get_awaiting_tool_calls("Friday") == []
    assert final is not None and final.finished_reason == "interrupted"


def test_interrupted_state_serializes_and_agent_recovers() -> None:
    tool = CountingTool()
    agent = _park_agent_on_confirmation(tool)

    # The parked (pre-interrupt) state round-trips through JSON without
    # losing the pending tool call.
    parked_json = agent.state.model_dump_json()
    restored = AgentState.model_validate_json(parked_json)
    assert restored.get_awaiting_tool_calls("Friday")[0].id == "call-1"

    # After the interrupt the agent runs a fresh reply on the same state.
    _interrupt(agent)
    model = FakeChatModel(
        [ChatResponse(content=[TextBlock(text="recovered")], is_last=True)],
    )
    agent.model = model
    reply = asyncio.run(agent.reply(UserMsg("Alice", "again")))
    assert reply.get_text_content() == "recovered"
    assert tool.executions == 0


def _interrupt(agent: Agent):
    async def run():
        events = []
        async for item in agent.reply_stream(
            UserInterruptEvent(reply_id=agent.state.reply_id),
        ):
            if item.__class__.__name__ != "Msg":
                events.append(item)
        return events

    return asyncio.run(run())


def test_parked_state_serialization_round_trip() -> None:
    tool = CountingTool()
    agent = _park_agent_on_confirmation(tool)

    restored = AgentState.model_validate_json(agent.state.model_dump_json())
    assert restored.get_awaiting_tool_calls("Friday")[0].id == "call-1"

    # The restored state can be attached to a fresh agent and resumed; the
    # model's next response is the final text.
    model = FakeChatModel(
        [ChatResponse(content=[TextBlock(text="resumed done")], is_last=True)],
    )
    resumed_agent = Agent(
        "Friday",
        "Prompt",
        model,
        state=restored,
        toolkit=Toolkit(tools=[tool]),
        permission_engine=PermissionEngine(
            PermissionContext(mode=PermissionMode.DEFAULT),
        ),
    )
    pending = restored.get_awaiting_tool_calls("Friday")
    confirm = UserConfirmResultEvent(
        reply_id=restored.reply_id,
        confirm_results=[{"confirmed": True, "tool_call": pending[0]}],
    )

    async def run():
        final = None
        async for item in resumed_agent.reply_stream(confirm):
            if item.__class__.__name__ == "Msg":
                final = item
        return final

    final = asyncio.run(run())
    assert tool.executions == 1
    assert final is not None
