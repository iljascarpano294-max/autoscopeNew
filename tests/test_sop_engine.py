"""Stage 9 task 3: SOPEngine sequential execution and recovery."""

import asyncio
import json

import pytest

from agentscope.agent import Agent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionEngine,
)
from agentscope.event import UserConfirmResultEvent
from agentscope.sop import (
    SOP,
    SOPPhase,
    SOPRunState,
    SOPStep,
    SOPStepRunState,
    SOPEngine,
    VerificationResult,
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
            message="defer",
        )

    async def call(self, *, a: int, b: int) -> ToolChunk:
        self.executions += 1
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


def _agents():
    """A planner agent whose text feeds an executor agent."""
    planner = Agent(
        "Planner",
        "Plan",
        FakeChatModel([
            _text_response("the plan is A then B"),
            _text_response("the plan is A then B"),
            _text_response("the plan is A then B"),
        ]),
    )
    executor = Agent("Executor", "Execute", FakeChatModel([_text_response("executed A and B")]))
    return planner, executor


def _two_step_sop(planner, executor) -> SOP:
    return SOP(
        name="plan-execute",
        steps=[
            SOPStep(planner, subject="planning"),
            SOPStep(executor, subject="executing"),
        ],
    )


def test_two_agents() -> None:
    planner, executor = _agents()
    sop = _two_step_sop(planner, executor)
    engine = SOPEngine(sop)

    async def run():
        events, final = [], None
        async for item in engine.reply_stream(UserMsg("Alice", "build it")):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    events, final = asyncio.run(run())

    # The final result comes from the second agent.
    assert final is not None
    assert final.get_text_content() == "executed A and B"
    assert engine.state.phase == SOPPhase.COMPLETED
    # Each agent ran exactly once and kept its own context.
    assert len(planner.model.calls) == 1
    assert len(executor.model.calls) == 1
    assert planner.state.context[-1] is not executor.state.context[-1]
    # The executor received the planner's text as a handover message.
    executor_sent = executor.model.calls[0][0]
    assert any("the plan is A then B" in (m.get_text_content() or "") for m in executor_sent)
    assert events  # the steps streamed their events through


def test_failure_retry() -> None:
    planner, executor = _agents()
    sop = _two_step_sop(planner, executor)
    attempts = {"n": 0}

    async def verify(given, submission):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return VerificationResult(passed=False, message="plan too vague")
        return VerificationResult(passed=True)

    sop.steps[0] = SOPStep(planner, subject="planning", verify=verify)
    engine = SOPEngine(sop)

    async def run():
        async for _ in engine.reply_stream(UserMsg("Alice", "build it")):
            pass

    asyncio.run(run())

    assert attempts["n"] == 2
    assert len(planner.model.calls) == 2  # retried once
    assert engine.state.phase == SOPPhase.COMPLETED
    # The refusal feedback reached the retry attempt.
    second_sent = planner.model.calls[1][0]
    assert any("plan too vague" in (m.get_text_content() or "") for m in second_sent)


def test_max_attempts_exhausted() -> None:
    planner, executor = _agents()
    sop = _two_step_sop(planner, executor)

    async def verify(given, submission):
        return VerificationResult(passed=False, message="never good enough")

    sop.steps[0] = SOPStep(planner, subject="planning", max_attempts=2, verify=verify)
    engine = SOPEngine(sop)

    async def run():
        async for _ in engine.reply_stream(UserMsg("Alice", "build it")):
            pass

    asyncio.run(run())

    assert engine.state.phase == SOPPhase.FAILED
    assert len(planner.model.calls) == 2  # budget spent, no more tries
    assert len(executor.model.calls) == 0  # later steps never ran


def test_confirmation_park_and_resume() -> None:
    tool = CountingTool()
    planner = Agent("Planner", "Plan", FakeChatModel([_text_response("plan ready")]))
    executor = Agent(
        "Executor",
        "Execute",
        FakeChatModel([_tool_call_turn(), _text_response("executed A and B")]),
        toolkit=Toolkit(tools=[tool]),
        permission_engine=PermissionEngine(PermissionContext()),
    )
    sop = _two_step_sop(planner, executor)
    engine = SOPEngine(sop)

    async def first_pass():
        events, final = [], None
        async for item in engine.reply_stream(UserMsg("Alice", "build it")):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    events, final = asyncio.run(first_pass())

    # The executor parked on tool confirmation: the run is awaiting, the
    # tool never ran, and the stream ended without a run result (the last
    # item is the parked step's event, not a final Msg).
    assert engine.state.phase == SOPPhase.AWAITING
    assert tool.executions == 0
    assert events[-1].__class__.__name__ != "Msg"

    # Resume with the confirmation; only the parked step continues.
    pending = executor.state.get_awaiting_tool_calls("Executor")
    confirm = UserConfirmResultEvent(
        reply_id=executor.state.reply_id,
        confirm_results=[{"confirmed": True, "tool_call": pending[0]}],
    )

    async def resume():
        final = None
        async for item in engine.reply_stream(confirm):
            if item.__class__.__name__ == "Msg":
                final = item
        return final

    final = asyncio.run(resume())

    assert tool.executions == 1
    assert final is not None and final.get_text_content() == "executed A and B"
    assert engine.state.phase == SOPPhase.COMPLETED
    # The planner was not re-run on resume.
    assert len(planner.model.calls) == 1


def test_state_step_count_mismatch_is_rejected() -> None:
    planner, executor = _agents()
    sop = _two_step_sop(planner, executor)
    stale_state = SOPRunState(steps=[SOPStepRunState()])

    with pytest.raises(ValueError, match="steps"):
        SOPEngine(sop, state=stale_state)
