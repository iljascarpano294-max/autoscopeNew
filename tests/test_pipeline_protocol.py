"""Stage 9 task 1: the pipeline protocol satisfied by Agent."""

import asyncio

from agentscope.agent import Agent
from agentscope.event import ReplyEndEvent, ReplyStartEvent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.pipeline import PipelineProtocol


def test_agent_as_pipeline() -> None:
    agent = Agent(
        "Friday",
        "Prompt",
        FakeChatModel([ChatResponse(content=[TextBlock(text="hi there")], is_last=True)]),
    )

    # The agent satisfies the structural pipeline protocol.
    assert isinstance(agent, PipelineProtocol)

    async def caller(pipeline: PipelineProtocol):
        """A caller that only knows the protocol, not the Agent class."""
        events, final = [], None
        async for item in pipeline.reply_stream(UserMsg("Alice", "Hi")):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    events, final = asyncio.run(caller(agent))

    # The event and final-message order is unchanged from a direct call.
    assert isinstance(events[0], ReplyStartEvent)
    assert any(isinstance(event, ReplyEndEvent) for event in events)
    assert final is not None and final.get_text_content() == "hi there"
    assert final is agent.state.context[-1]
