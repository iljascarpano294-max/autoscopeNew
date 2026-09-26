"""Stage 11 task 2: the chat service backed by durable storage."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.app._service import ChatService, SessionService
from agentscope.app.storage import SQLiteStorage
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


def _factory(responses: list | None = None):
    def build() -> Agent:
        return Agent(
            "Friday",
            "Be concise",
            FakeChatModel(
                responses
                if responses is not None
                else [ChatResponse(content=[TextBlock(text="ok")], is_last=True)],
            ),
        )

    return build


def test_chat_after_restart(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"

    async def first_process():
        storage = SQLiteStorage(db_path)
        sessions = SessionService(
            agent_factory=_factory(
                [
                    ChatResponse(content=[TextBlock(text="ok")], is_last=True),
                    ChatResponse(content=[TextBlock(text="ok")], is_last=True),
                ],
            ),
            storage=storage,
        )
        chat = ChatService(sessions)
        session_id = sessions.create(agent_id="demo").session_id

        await chat.send(session_id, "question one")
        await chat.send(session_id, "question two")
        await storage.close()
        return session_id

    session_id = asyncio.run(first_process())

    # A new process rebuilds the services over the same database; the
    # restored agent's next reply continues the conversation.
    responses = [
        ChatResponse(content=[TextBlock(text="third reply")], is_last=True),
    ]

    async def second_process():
        storage = SQLiteStorage(db_path)
        sessions = SessionService(agent_factory=_factory(responses), storage=storage)
        chat = ChatService(sessions)
        record = await sessions.load(session_id)
        reply = await chat.send(session_id, "question three")
        await storage.close()
        return record, reply

    record, reply = asyncio.run(second_process())

    assert reply.get_text_content() == "third reply"
    agent = record.agent
    third_sent = agent.model.calls[0][0]
    roles = [msg.role for msg in third_sent]
    # system + two old turns + the new question: the old history survived.
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert third_sent[1].get_text_content() == "question one"


def test_failed_turn_is_not_persisted(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"

    async def run():
        storage = SQLiteStorage(db_path)
        sessions = SessionService(
            agent_factory=_factory(
                [
                    RuntimeError("model down"),
                    ChatResponse(content=[TextBlock(text="ok")], is_last=True),
                ],
            ),
            storage=storage,
        )
        chat = ChatService(sessions)
        session_id = sessions.create(agent_id="demo").session_id

        with pytest.raises(RuntimeError, match="model down"):
            await chat.send(session_id, "hello")

        # The next turn works and only its own history is present.
        reply = await chat.send(session_id, "hello again")
        await storage.close()
        return reply

    reply = asyncio.run(run())
    assert reply.get_text_content() == "ok"


def test_corrupted_state_is_reported(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"

    async def run():
        storage = SQLiteStorage(db_path)
        sessions = SessionService(agent_factory=_factory(), storage=storage)
        session_id = sessions.create(agent_id="demo").session_id
        await chat_send_once(sessions, chat := ChatService(sessions), session_id)
        await storage.close()

        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE messages SET msg = '{not json'")
        conn.commit()
        conn.close()

        storage = SQLiteStorage(db_path)
        sessions = SessionService(agent_factory=_factory(), storage=storage)
        try:
            await sessions.load(session_id)
        finally:
            await storage.close()

    from agentscope.app.storage import StorageError

    with pytest.raises(StorageError, match="corrupted"):
        asyncio.run(run())


async def chat_send_once(sessions, chat, session_id):
    await chat.send(session_id, "hi")
