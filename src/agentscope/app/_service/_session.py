# -*- coding: utf-8 -*-
"""In-process session records and the session service.

Stage 11 adds an optional durable store: when one is attached, the chat
service snapshots the session after every completed turn, and a restart
can rebuild the session from storage via :meth:`load`.
"""
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..._utils._common import _generate_id, _generate_timestamp


class SessionNotFound(Exception):
    """The requested session id does not exist (or was deleted)."""


class SessionRecord(BaseModel):
    """One chat session: the agent instance plus its bookkeeping."""

    model_config = {"arbitrary_types_allowed": True}

    session_id: str = Field(default_factory=_generate_id)
    """The unique session identifier."""

    agent_id: str
    """Which agent definition this session runs."""

    agent: Any
    """The live agent instance (an Agent, or anything satisfying the
    pipeline protocol); it owns the conversation state."""

    created_at: str = Field(default_factory=_generate_timestamp)
    """When the session was created."""

    last_active_at: str = Field(default_factory=_generate_timestamp)
    """When the session last processed a message."""


class SessionService:
    """Create, look up and drop sessions in process memory, optionally
    backed by durable storage."""

    def __init__(self, agent_factory: Callable[[], Any], storage: Any | None = None) -> None:
        """Initialize the service.

        Args:
            agent_factory (`Callable[[], Any]`):
                Called for every new (or restored) session to build its
                agent instance; inject a factory over a Fake model in
                tests.
            storage (`StorageBase | None`, optional):
                When given, completed turns are persisted and
                :meth:`load` can restore sessions after a restart.
        """
        self._agent_factory = agent_factory
        self.storage = storage
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, agent_id: str) -> SessionRecord:
        """Register a new session, building its agent via the factory."""
        record = SessionRecord(agent_id=agent_id, agent=self._agent_factory())
        self._sessions[record.session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        """Return the in-memory record, raising SessionNotFound when unknown."""
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFound(
                f"Session '{session_id}' was not found; it may have been "
                f"deleted, or the process restarted.",
            ) from None

    async def load(self, session_id: str) -> SessionRecord:
        """Return the session from memory, or restore it from storage.

        Raises:
            `SessionNotFound`:
                If the session is neither in memory nor in storage.
        """
        if session_id in self._sessions:
            return self._sessions[session_id]
        if self.storage is None:
            raise SessionNotFound(
                f"Session '{session_id}' was not found; it may have been "
                f"deleted, or the process restarted.",
            )
        record = await self.storage.load_session(
            session_id,
            agent_factory=self._agent_factory,
        )
        self._sessions[session_id] = record
        return record

    async def persist(self, record: SessionRecord, turn_msgs: list) -> None:
        """Snapshot the session state and its new turn messages.

        Called by the chat service only after a turn completed, so a
        failed model call never reaches storage.
        """
        if self.storage is None:
            return
        await self.storage.save_session(record)
        for msg in turn_msgs:
            await self.storage.append_message(record.session_id, msg)

    def delete(self, session_id: str) -> None:
        """Drop the session; unknown ids are reported."""
        if session_id not in self._sessions:
            raise SessionNotFound(
                f"Session '{session_id}' was not found; it may have been "
                f"deleted, or the process restarted.",
            )
        del self._sessions[session_id]

    def clear(self) -> None:
        """Release every session (used on application shutdown)."""
        self._sessions.clear()
