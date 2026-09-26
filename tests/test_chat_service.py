"""Stage 10 task 2: chat service with per-session serialization."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.app._service import ChatService, SessionService
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel


def _agent(responses: list) -> Agent:
    return Agent("Friday", "Be concise", FakeChatModel(responses))


def test_chat_turns_keep_history_order() -> None:
    service = SessionService(
        agent_factory=lambda: _agent(
            [
                ChatResponse(content=[TextBlock(text="first reply")], is_last=True),
                ChatResponse(content=[TextBlock(text="second reply")], is_last=True),
            ],
        ),
    )
    chat = ChatService(service)
    session_id = service.create(agent_id="demo").session_id

    first = asyncio.run(chat.send(session_id, "one"))
    second = asyncio.run(chat.send(session_id, "two"))

    assert first.get_text_content() == "first reply"
    assert second.get_text_content() == "second reply"

    # The second model call saw the full ordered history.
    agent = service.get(session_id).agent
    second_sent = agent.model.calls[1][0]
    roles = [msg.role for msg in second_sent]
    assert roles == ["system", "user", "assistant", "user"]


def test_concurrent_sends_serialize_per_session() -> None:
    service = SessionService(
        agent_factory=lambda: _agent(
            [
                ChatResponse(content=[TextBlock(text="reply one")], is_last=True),
                ChatResponse(content=[TextBlock(text="reply two")], is_last=True),
            ],
        ),
    )
    chat = ChatService(service)
    session_id = service.create(agent_id="demo").session_id

    async def run():
        return await asyncio.gather(
            chat.send(session_id, "first message"),
            chat.send(session_id, "second message"),
        )

    replies = asyncio.run(run())

    # Same-session requests run one at a time, in the order the lock was
    # acquired; no interleaving of model calls.
    assert [reply.get_text_content() for reply in replies] == [
        "reply one",
        "reply two",
    ]
    agent = service.get(session_id).agent
    assert len(agent.model.calls) == 2


def test_concurrent_sends_in_different_sessions_are_independent() -> None:
    service = SessionService(
        agent_factory=lambda: _agent(
            [ChatResponse(content=[TextBlock(text="ok")], is_last=True)],
        ),
    )
    chat = ChatService(service)
    first_id = service.create(agent_id="demo").session_id
    second_id = service.create(agent_id="demo").session_id

    async def run():
        return await asyncio.gather(
            chat.send(first_id, "hello"),
            chat.send(second_id, "hello"),
        )

    replies = asyncio.run(run())
    assert [reply.get_text_content() for reply in replies] == ["ok", "ok"]


def test_model_error_leaves_no_fake_reply() -> None:
    service = SessionService(
        agent_factory=lambda: _agent(
            [
                RuntimeError("model down"),
                ChatResponse(content=[TextBlock(text="recovered")], is_last=True),
            ],
        ),
    )
    chat = ChatService(service)
    session_id = service.create(agent_id="demo").session_id

    with pytest.raises(RuntimeError, match="model down"):
        asyncio.run(chat.send(session_id, "hello"))

    # No assistant message was appended for the failed turn.
    agent = service.get(session_id).agent
    assert [msg.role for msg in agent.state.context] == ["user"]

    # The lock was released; the next turn works.
    reply = asyncio.run(chat.send(session_id, "hello again"))
    assert reply.get_text_content() == "recovered"


def test_unknown_session_is_reported() -> None:
    from agentscope.app._service import SessionNotFound

    service = SessionService(agent_factory=_agent)
    chat = ChatService(service)

    with pytest.raises(SessionNotFound):
        asyncio.run(chat.send("missing", "hi"))
