"""Stage 9 demo: two agents collaborating on one goal.

The GoalPipeline drives the members in order: the goal opens the first
member's reply, each later member receives the previous result as a
handover message, and a failing member surfaces as a traceable
MEMBER_FAILED CustomEvent. Every member keeps its own conversation
context; only text crosses the boundary.
"""

import asyncio

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.pipeline import GoalPipeline


async def main() -> None:
    planner = Agent(
        "Planner",
        "You plan the work.",
        FakeChatModel(
            [
                ChatResponse(content=[TextBlock(text="Plan: write the tests, then the code.")], is_last=True),
            ],
        ),
    )
    executor = Agent(
        "Executor",
        "You execute the plan.",
        FakeChatModel(
            [
                ChatResponse(content=[TextBlock(text="Tests and code are written.")], is_last=True),
            ],
        ),
    )
    pipeline = GoalPipeline(
        goal="Implement the add function.",
        members=[planner, executor],
    )

    print("goal: Implement the add function.")
    async for item in pipeline.reply_stream():
        if item.__class__.__name__ == "Msg":
            print(f"result: {item.get_text_content()}")
        elif getattr(item, "type", "") == "CUSTOM":
            print(f"event: {item.name} {item.value}")

    # A failing member produces a traceable failure event.
    broken = Agent(
        "Broken",
        "Prompt",
        FakeChatModel([RuntimeError("model down")]),
    )
    failing = GoalPipeline(goal="ship", members=[broken, executor])
    print("\nfailing run:")
    async for item in failing.reply_stream():
        if getattr(item, "type", "") == "CUSTOM" and item.name == "MEMBER_FAILED":
            print(f"event: {item.name} member={item.value['member']} error={item.value['error']}")


if __name__ == "__main__":
    asyncio.run(main())
