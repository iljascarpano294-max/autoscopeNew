"""Stage 3 non-streaming Agent behavior."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.message import AssistantMsg, TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, ChatUsage, FakeChatModel
from agentscope.state import AgentState


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


def test_state_is_independent_and_injectable() -> None:
    first = AgentState()
    second = AgentState()
    first.context.append(UserMsg("A", "Hi"))
    assert second.context == []
    agent = Agent("Friday", "Be helpful", FakeChatModel([]), state=first)
    assert agent.state is first


def test_two_turns_preserve_order_and_system_prompt() -> None:
    model = FakeChatModel([_text_response("Hello"), _text_response("Goodbye")])
    agent = Agent("Friday", "Be concise", model)

    first = asyncio.run(agent.reply(UserMsg("Alice", "Hi")))
    second = asyncio.run(agent.reply(UserMsg("Alice", "Bye")))

    assert first.role == second.role == "assistant"
    assert first.name == "Friday"
    assert second.get_text_content() == "Goodbye"
    assert [msg.role for msg in agent.state.context] == ["user", "assistant", "user", "assistant"]
    sent = model.calls[1][0]
    assert [msg.role for msg in sent] == ["system", "user", "assistant", "user"]
    assert sent[0].get_text_content() == "Be concise"
    assert sent[2].get_text_content() == "Hello"


def test_observe_stores_without_model_call() -> None:
    model = FakeChatModel([_text_response("OK")])
    agent = Agent("Friday", "Prompt", model)
    asyncio.run(agent.observe([UserMsg("A", "one"), AssistantMsg("B", "two")]))
    assert len(agent.state.context) == 2
    assert model.calls == []
    reply = asyncio.run(agent.reply(UserMsg("A", "three")))
    assert reply.get_text_content() == "OK"
    assert len(model.calls[0][0]) == 4


def test_usage_maps_to_reply_message() -> None:
    response = _text_response("Hello")
    response.usage = ChatUsage(input_tokens=7, output_tokens=2, time=0.3)
    agent = Agent("Friday", "Prompt", FakeChatModel([response]))
    reply = asyncio.run(agent.reply(UserMsg("A", "Hi")))
    assert reply.usage.input_tokens == 7
    assert reply.usage.output_tokens == 2
    assert reply.finished_at is not None


def test_tool_call_is_not_silently_ignored() -> None:
    response = ChatResponse(
        content=[ToolCallBlock(id="call-1", name="weather", input="{}")], is_last=True
    )
    agent = Agent("Friday", "Prompt", FakeChatModel([response]))
    with pytest.raises(NotImplementedError, match="stage 4"):
        asyncio.run(agent.reply(UserMsg("A", "Weather?")))
    assert [msg.role for msg in agent.state.context] == ["user"]


def test_model_error_does_not_create_assistant_reply() -> None:
    agent = Agent("Friday", "Prompt", FakeChatModel([RuntimeError("model down")]))
    with pytest.raises(RuntimeError, match="model down"):
        asyncio.run(agent.reply(UserMsg("A", "Hi")))
    assert [msg.role for msg in agent.state.context] == ["user"]
