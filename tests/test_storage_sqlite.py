"""Stage 11 task 1: the storage contract and the SQLite implementation."""

import asyncio
import json

import pytest

from agentscope.agent import Agent
from agentscope.app.storage import SQLiteStorage, StorageError
from agentscope.message import AssistantMsg, TextBlock, UserMsg


def _agent() -> Agent:
    return Agent("Friday", "Be concise", None)


def _record_with_turns() -> tuple:
    agent = _agent()
    agent.state.context.extend(
        [
            UserMsg("Alice", "question one"),
            AssistantMsg("Friday", "answer one"),
            UserMsg("Alice", "question two"),
            AssistantMsg("Friday", "answer two"),
        ],
    )
    from agentscope.app._service import SessionRecord

    record = SessionRecord(agent_id="demo", agent=agent)
    return record, agent


def test_restart_restore(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"
    record, agent = _record_with_turns()
    session_id = record.session_id

    async def save():
        storage = SQLiteStorage(db_path)
        await storage.save_session(record)
        await storage.append_message(session_id, agent.state.context[0])
        await storage.append_message(session_id, agent.state.context[1])
        await storage.append_message(session_id, agent.state.context[2])
        await storage.append_message(session_id, agent.state.context[3])
        await storage.close()

    asyncio.run(save())

    # A second instance (simulating a process restart) loads the session.
    async def load():
        storage = SQLiteStorage(db_path)
        restored = await storage.load_session(session_id, agent_factory=_agent)
        await storage.close()
        return restored

    restored = asyncio.run(load())

    assert restored.session_id == session_id
    assert restored.agent_id == "demo"
    restored_context = restored.agent.state.context
    assert [msg.role for msg in restored_context] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert restored_context[0].get_text_content() == "question one"
    assert restored_context[3].get_text_content() == "answer two"


def test_failed_append_leaves_no_partial_record(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"

    async def run():
        record, agent = _record_with_turns()
        storage = SQLiteStorage(db_path)
        await storage.save_session(record)
        await storage.append_message(record.session_id, agent.state.context[0])
        before = await storage.count_messages(record.session_id)

        # An unserializable message must fail the whole append.
        with pytest.raises(StorageError):
            await storage.append_message(record.session_id, object())
        after = await storage.count_messages(record.session_id)
        await storage.close()
        return before, after

    before, after = asyncio.run(run())
    assert before == 1
    assert after == 1  # nothing partial was written


def test_incompatible_schema_version_is_rejected(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"
    record, _agent_ = _record_with_turns()

    async def run():
        storage = SQLiteStorage(db_path)
        await storage.save_session(record)
        await storage.close()
        # Corrupt the stored schema version to something from the future.
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE sessions SET schema_version = 999")
        conn.commit()
        conn.close()

        storage = SQLiteStorage(db_path)
        try:
            await storage.load_session(record.session_id, agent_factory=_agent)
        finally:
            await storage.close()

    with pytest.raises(StorageError, match="version"):
        asyncio.run(run())
