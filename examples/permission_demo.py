"""Stage 6 demo: allow, deny, ask-then-confirm, and interrupt paths.

All four paths run offline against one CountingTool whose executions counter
proves when a tool really ran:

1. ALLOW rule  -> the engine allows the call, the tool executes.
2. DENY rule   -> the engine denies it, a DENIED tool result is recorded.
3. ASK (DEFAULT mode, no rules) -> the reply parks on
   RequireUserConfirmEvent; the user confirms, the reply resumes and the
   tool executes exactly once.
4. INTERRUPT   -> a parked reply is aborted; every pending call is closed
   with an INTERRUPTED tool result, and AgentState serializes cleanly.
"""

import asyncio
import json

from agentscope.agent import Agent
from agentscope.event import UserConfirmResultEvent, UserInterruptEvent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
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


def _build(model_responses, rules=()) -> tuple:
    tool = CountingTool()
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    for rule in rules:
        engine.add_rule(rule)
    model = FakeChatModel(model_responses)
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[tool]),
        permission_engine=engine,
    )
    return agent, tool


async def _collect(agent, inputs):
    final = None
    async for item in agent.reply_stream(inputs):
        if item.__class__.__name__ == "Msg":
            final = item
        else:
            yield item
    yield final


async def main() -> None:
    # 1. ALLOW rule: the tool runs immediately.
    agent, tool = _build(
        [_tool_call_turn("call-1"), _text_response("allowed path done")],
        rules=[
            PermissionRule(
                tool_name="count_add",
                rule_content=None,
                behavior=PermissionBehavior.ALLOW,
                source="userSettings",
            ),
        ],
    )
    async for item in _collect(agent, UserMsg("Alice", "add")):
        if item.__class__.__name__ == "Msg":
            print(f"[allow]    executions={tool.executions} reply={item.get_text_content()!r}")

    # 2. DENY rule: the tool never runs, a denied result is recorded.
    agent, tool = _build(
        [_tool_call_turn("call-2"), _text_response("denied path done")],
        rules=[
            PermissionRule(
                tool_name="count_add",
                rule_content=None,
                behavior=PermissionBehavior.DENY,
                source="userSettings",
            ),
        ],
    )
    async for item in _collect(agent, UserMsg("Alice", "add")):
        if item.__class__.__name__ == "Msg":
            print(f"[deny]     executions={tool.executions} reply={item.get_text_content()!r}")

    # 3. ASK: the reply parks, the user confirms, the tool runs once.
    agent, tool = _build(
        [_tool_call_turn("call-3"), _text_response("confirmed path done")],
    )
    pending_confirm = None
    async for item in _collect(agent, UserMsg("Alice", "add")):
        if item.__class__.__name__ == "RequireUserConfirmEvent":
            pending_confirm = item
            print(f"[ask]      parked, executions={tool.executions}")
    pending = agent.state.get_awaiting_tool_calls("Friday")
    async for item in _collect(
        agent,
        UserConfirmResultEvent(
            reply_id=agent.state.reply_id,
            confirm_results=[{"confirmed": True, "tool_call": pending[0]}],
        ),
    ):
        if item.__class__.__name__ == "Msg":
            print(f"[confirm]  executions={tool.executions} reply={item.get_text_content()!r}")

    # 4. INTERRUPT: a parked reply is aborted with explainable state.
    agent, tool = _build([_tool_call_turn("call-4")])
    async for item in _collect(agent, UserMsg("Alice", "add")):
        if item.__class__.__name__ == "RequireUserConfirmEvent":
            print(f"[ask]      parked again, executions={tool.executions}")
    async for item in _collect(
        agent,
        UserInterruptEvent(reply_id=agent.state.reply_id),
    ):
        if item.__class__.__name__ == "Msg":
            print(
                f"[interrupt] executions={tool.executions} "
                f"pending={len(agent.state.get_awaiting_tool_calls('Friday'))} "
                f"reply_state={agent.state.model_dump_json()[:60]}...",
            )


if __name__ == "__main__":
    asyncio.run(main())
