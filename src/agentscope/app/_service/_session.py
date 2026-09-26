# -*- coding: utf-8 -*-
"""In-process session records and the session service.

Stage 10 keeps sessions in a process-local dictionary: a restart loses
them and lookups report not-found. Durable storage arrives in stage 11.
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
    """Create, look up and drop sessions in process memory."""

    def __init__(self, agent_factory: Callable[[], Any]) -> None:
        """Initialize the service.

        Args:
            agent_factory (`Callable[[], Any]`):
                Called for every new session to build its agent instance;
                inject a factory over a Fake model in tests.
        """
        self._agent_factory = agent_factory
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, agent_id: str) -> SessionRecord:
        """Register a new session, building its agent via the factory."""
        record = SessionRecord(agent_id=agent_id, agent=self._agent_factory())
        self._sessions[record.session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        """Return the record, raising SessionNotFound when unknown."""
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFound(
                f"Session '{session_id}' was not found; it may have been "
                f"deleted, or the process restarted.",
            ) from None

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
