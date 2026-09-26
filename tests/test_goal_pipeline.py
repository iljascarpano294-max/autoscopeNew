"""Stage 9 task 4: the goal-driven pipeline slice."""

import asyncio

from agentscope.agent import Agent
from agentscope.event import CustomEvent
from agentscope.message import Msg, TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.pipeline import GoalPipeline


def _agent(name: str, text: str) -> Agent:
    return Agent(
        name,
        "Prompt",
        FakeChatModel([ChatResponse(content=[TextBlock(text=text)], is_last=True)]),
    )


def _collect(pipeline: GoalPipeline):
    async def run():
        events, final = [], None
        async for item in pipeline.reply_stream():
            if isinstance(item, Msg):
                final = item
            else:
                events.append(item)
        return events, final

    return asyncio.run(run())


def test_goal_pipeline_normal_path() -> None:
    planner = _agent("Planner", "the plan")
    executor = _agent("Executor", "the result")
    pipeline = GoalPipeline(
        goal="ship the feature",
        members=[planner, executor],
    )

    events, final = _collect(pipeline)

    # Both members ran exactly once, in order, with independent contexts.
    assert len(planner.model.calls) == 1
    assert len(executor.model.calls) == 1
    assert planner.state.context is not executor.state.context
    assert final is not None and final.get_text_content() == "the result"

    # The goal started the run and the handover reached the second member.
    starts = [e for e in events if isinstance(e, CustomEvent) and e.name == "GOAL_STARTED"]
    assert len(starts) == 1
    assert starts[0].value["goal"] == "ship the feature"
    executor_sent = executor.model.calls[0][0]
    assert any("the plan" in (m.get_text_content() or "") for m in executor_sent)


def test_goal_pipeline_member_failure_is_traceable() -> None:
    failing = Agent(
        "Broken",
        "Prompt",
        FakeChatModel([RuntimeError("model down")]),
    )
    executor = _agent("Executor", "never reached")
    pipeline = GoalPipeline(
        goal="ship the feature",
        members=[failing, executor],
    )

    events, final = _collect(pipeline)

    failures = [
        event for event in events if isinstance(event, CustomEvent) and event.name == "MEMBER_FAILED"
    ]
    assert len(failures) == 1
    assert failures[0].value["member"] == "Broken"
    assert "model down" in failures[0].value["error"]
    assert final is None
    # The remaining member never ran.
    assert len(executor.model.calls) == 0
