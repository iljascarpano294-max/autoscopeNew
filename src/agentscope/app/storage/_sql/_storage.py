# -*- coding: utf-8 -*-
"""SQLite-backed session storage (stage 11 offline slice)."""
import json
import sqlite3
from typing import Any, Callable

from ..._service import SessionRecord
from ....message import Msg
from ....state import AgentState
from .._base import StorageBase, StorageError

_SCHEMA_VERSION = 1


class SQLiteStorage(StorageBase):
    """Store sessions in a local SQLite database file.

    Every write runs in a transaction, so a failed append never leaves a
    partial message record. The stored schema version is checked on load;
    anything newer than this build is refused with a clear error.
    """

    def __init__(self, db_path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    reply_id TEXT NOT NULL,
                    state_meta TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                )
                """,
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    session_id TEXT NOT NULL REFERENCES sessions(session_id),
                    seq INTEGER NOT NULL,
                    msg TEXT NOT NULL,
                    PRIMARY KEY (session_id, seq)
                )
                """,
            )

    async def save_session(self, record: SessionRecord) -> None:
        state = record.agent.state
        state_meta = state.model_dump(exclude={"context"})
        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, agent_id, reply_id, state_meta,
                        created_at, last_active_at, schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        agent_id = excluded.agent_id,
                        reply_id = excluded.reply_id,
                        state_meta = excluded.state_meta,
                        last_active_at = excluded.last_active_at,
                        schema_version = excluded.schema_version
                    """,
                    (
                        record.session_id,
                        record.agent_id,
                        state.reply_id,
                        json.dumps(state_meta),
                        record.created_at,
                        record.last_active_at,
                        _SCHEMA_VERSION,
                    ),
                )
        except sqlite3.Error as error:
            raise StorageError(f"Failed to save session: {error}") from error

    async def load_session(
        self,
        session_id: str,
        agent_factory: Callable[[], Any] | None = None,
    ) -> SessionRecord:
        row = self._conn.execute(
            """
            SELECT session_id, agent_id, reply_id, state_meta, created_at,
                   last_active_at, schema_version
            FROM sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            from .._service import SessionNotFound

            raise SessionNotFound(
                f"Session '{session_id}' was not found in storage.",
            )
        (
            stored_id,
            agent_id,
            reply_id,
            state_meta_json,
            created_at,
            last_active_at,
            schema_version,
        ) = row

        if schema_version > _SCHEMA_VERSION:
            raise StorageError(
                f"Stored session '{session_id}' uses schema version "
                f"{schema_version}, newer than the supported version "
                f"{_SCHEMA_VERSION}; refusing to load.",
            )

        context_rows = self._conn.execute(
            "SELECT msg FROM messages WHERE session_id = ? ORDER BY seq",
            (session_id,),
        ).fetchall()
        try:
            context = [Msg.model_validate_json(row[0]) for row in context_rows]
            state_meta = json.loads(state_meta_json)
        except (json.JSONDecodeError, ValueError) as error:
            raise StorageError(
                f"Stored session '{session_id}' is corrupted: {error}",
            ) from error

        if agent_factory is None:
            raise StorageError(
                "load_session requires an agent_factory to rebuild the "
                "session's agent.",
            )
        agent = agent_factory()
        agent.state = AgentState(
            context=context,
            reply_id=state_meta.get("reply_id", reply_id),
            middle_context=state_meta.get("middle_context", {}),
        )
        return SessionRecord(
            session_id=stored_id,
            agent_id=agent_id,
            agent=agent,
            created_at=created_at,
            last_active_at=last_active_at,
        )

    async def append_message(self, session_id: str, msg: Msg) -> None:
        try:
            payload = msg.model_dump_json() if isinstance(msg, Msg) else None
            if payload is None:
                raise StorageError(
                    f"Cannot append an object of type {type(msg).__name__}; "
                    f"expected Msg.",
                )
            with self._conn:
                row = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), -1) FROM messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                next_seq = row[0] + 1
                self._conn.execute(
                    "INSERT INTO messages (session_id, seq, msg) VALUES (?, ?, ?)",
                    (session_id, next_seq, payload),
                )
        except sqlite3.Error as error:
            raise StorageError(f"Failed to append message: {error}") from error

    async def count_messages(self, session_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row[0])

    async def close(self) -> None:
        self._conn.close()
