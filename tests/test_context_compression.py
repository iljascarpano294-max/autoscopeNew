"""Stage 7 task 3: context compression middleware."""

import asyncio

from agentscope.agent import Agent
from agentscope.message import AssistantMsg, Msg, TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.middleware import ContextCompressionMiddleware
from agentscope.state import AgentState


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


def _summary_of(msgs: list[Msg]) -> str:
    return f"summary of {len(msgs)} messages"


def _compressing_agent(context: list[Msg]) -> Agent:
    model = FakeChatModel([_text_response("done")])
    middleware = ContextCompressionMiddleware(
        max_messages=4,
        keep_recent=2,
        summarize=_summary_of,
    )
    return Agent(
        "Friday",
        "You are helpful.",
        model,
        state=AgentState(context=context),
        middlewares=[middleware],
    )


def _turns(n: int) -> list[Msg]:
    turns = []
    for i in range(n):
        turns.append(UserMsg("Alice", f"question {i}"))
        turns.append(AssistantMsg("Friday", f"answer {i}"))
    return turns


def test_compress_context() -> None:
    context = _turns(3)  # 6 messages
    agent = _compressing_agent(context)
    assert len(agent.state.context) == 6

    asyncio.run(agent.reply(UserMsg("Alice", "final question")))

    # The old messages collapsed into one summary; the system prompt is
    # rebuilt per call so it is never lost, and the recent turns plus the
    # new exchange remain intact.
    compressed = agent.state.context
    summary = compressed[0]
    assert summary.name == "context_summary"
    assert summary.get_text_content() == "summary of 4 messages"
    assert [msg.role for msg in compressed[1:]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]

    sent = agent.model.calls[0][0]
    assert sent[0].get_text_content() == "You are helpful."
    assert sent[1].get_text_content() == "summary of 4 messages"


def test_below_threshold_context_unchanged() -> None:
    context = _turns(1)  # 2 messages, below max_messages=4
    agent = _compressing_agent(context)

    asyncio.run(agent.reply(UserMsg("Alice", "final question")))

    assert agent.state.context[0] is context[0]
    assert agent.state.context[1] is context[1]
    assert [msg.name for msg in agent.state.context[:2]] == ["Alice", "Friday"]


def test_summary_messages_are_not_recompressed() -> None:
    model = FakeChatModel([_text_response("done"), _text_response("done again")])
    middleware = ContextCompressionMiddleware(
        max_messages=4,
        keep_recent=2,
        summarize=_summary_of,
    )
    context = _turns(3)
    agent = Agent(
        "Friday",
        "You are helpful.",
        model,
        state=AgentState(context=context),
        middlewares=[middleware],
    )
    asyncio.run(agent.reply(UserMsg("Alice", "first")))

    first_summary_text = agent.state.context[0].get_text_content()

    # Grow the context past the threshold again and compress once more.
    for i in range(2):
        agent.state.context.append(UserMsg("Alice", f"extra {i}"))
        agent.state.context.append(AssistantMsg("Friday", f"extra answer {i}"))
    asyncio.run(agent.reply(UserMsg("Alice", "second")))

    summaries = [
        msg
        for msg in agent.state.context
        if msg.name == "context_summary"
    ]
    assert len(summaries) == 1
    # The old summary text is carried into the new one verbatim, and only
    # the six fresh messages are summarized this time.
    assert summaries[0].get_text_content() == (
        f"{first_summary_text}\nsummary of 6 messages"
    )
