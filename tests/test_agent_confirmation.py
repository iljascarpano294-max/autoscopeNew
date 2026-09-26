"""Stage 6 task 3: tool confirmation (ASK) and resume flow."""

import asyncio
import json

import pytest

from agentscope.agent import Agent
from agentscope.event import (
    RequireUserConfirmEvent,
    UserConfirmResultEvent,
)
from agentscope.message import TextBlock, ToolCallBlock, ToolResultState, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionEngine,
    PermissionMode,
    PermissionRule,
)
from agentscope.tool import ToolBase, ToolChunk, Toolkit


class CountingTool(ToolBase):
    name = "count_add"
    description = "Add two integers, counting executions."
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


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


def _agent(model: FakeChatModel, tool: CountingTool) -> Agent:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    return Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[tool]),
        permission_engine=engine,
    )


def _collect(agent: Agent, *inputs):
    async def run():
        events, final = [], None
        async for item in agent.reply_stream(*inputs):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    return asyncio.run(run())


def test_ask_parks_reply_without_executing_tool() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1")])
    agent = _agent(model, tool)

    events, final = _collect(agent, UserMsg("Alice", "add"))

    # The reply parked on the confirmation request: no execution, no final msg.
    assert tool.executions == 0
    assert final is None
    confirms = [e for e in events if isinstance(e, RequireUserConfirmEvent)]
    assert len(confirms) == 1
    assert confirms[0].tool_calls[0].id == "call-1"
    # The parked tool call is recorded in the context as ASKING.
    assistant = agent.state.context[-1]
    assert assistant.get_content_blocks("tool_call")[0].state == "asking"


def test_confirm_resumes_and_executes_once() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1"), _text_response("done")])
    agent = _agent(model, tool)
    _collect(agent, UserMsg("Alice", "add"))

    pending = agent.state.get_awaiting_tool_calls("Friday")
    assert [tc.id for tc in pending] == ["call-1"]

    confirm = UserConfirmResultEvent(
        reply_id=agent.state.reply_id,
        confirm_results=[
            {"confirmed": True, "tool_call": pending[0]},
        ],
    )
    events, final = _collect(agent, confirm)

    assert tool.executions == 1
    assert final is not None and final.get_text_content() == "done"
    assistant = agent.state.context[-1]
    result = assistant.get_content_blocks("tool_result")[0]
    assert result.state == ToolResultState.SUCCESS
    assert result.output[0].text == "5"


def test_duplicate_confirm_is_rejected_without_execution() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1"), _text_response("done")])
    agent = _agent(model, tool)
    _collect(agent, UserMsg("Alice", "add"))
    pending = agent.state.get_awaiting_tool_calls("Friday")

    confirm = UserConfirmResultEvent(
        reply_id=agent.state.reply_id,
        confirm_results=[{"confirmed": True, "tool_call": pending[0]}],
    )
    _collect(agent, confirm)
    assert tool.executions == 1

    # The same confirmation submitted again matches no awaiting call.
    with pytest.raises(ValueError, match="not waiting"):
        _collect(agent, confirm)
    assert tool.executions == 1


def test_wrong_confirm_id_is_rejected() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1")])
    agent = _agent(model, tool)
    _collect(agent, UserMsg("Alice", "add"))
    pending = agent.state.get_awaiting_tool_calls("Friday")

    stale_call = pending[0].model_copy(deep=True)
    stale_call.id = "wrong-id"
    confirm = UserConfirmResultEvent(
        reply_id=agent.state.reply_id,
        confirm_results=[{"confirmed": True, "tool_call": stale_call}],
    )
    with pytest.raises(ValueError, match="not waiting"):
        _collect(agent, confirm)
    assert tool.executions == 0


def test_denied_confirm_becomes_failed_result() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1"), _text_response("ok then")])
    agent = _agent(model, tool)
    _collect(agent, UserMsg("Alice", "add"))
    pending = agent.state.get_awaiting_tool_calls("Friday")

    confirm = UserConfirmResultEvent(
        reply_id=agent.state.reply_id,
        confirm_results=[{"confirmed": False, "tool_call": pending[0]}],
    )
    events, final = _collect(agent, confirm)

    assert tool.executions == 0
    assert final is not None and final.get_text_content() == "ok then"
    result = agent.state.context[-1].get_content_blocks("tool_result")[0]
    assert result.state == ToolResultState.DENIED


def test_allow_rule_skips_confirmation() -> None:
    tool = CountingTool()
    model = FakeChatModel([_tool_call_turn("call-1"), _text_response("done")])
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    engine.add_rule(
        PermissionRule(
            tool_name="count_add",
            rule_content=None,
            behavior=PermissionBehavior.ALLOW,
            source="userSettings",
        ),
    )
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[tool]),
        permission_engine=engine,
    )

    events, final = _collect(agent, UserMsg("Alice", "add"))

    assert tool.executions == 1
    assert final is not None and final.get_text_content() == "done"
    assert not [e for e in events if isinstance(e, RequireUserConfirmEvent)]
