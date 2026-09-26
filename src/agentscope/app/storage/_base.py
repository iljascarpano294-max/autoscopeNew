# -*- coding: utf-8 -*-
"""The storage contract for durable sessions."""
from abc import ABC, abstractmethod
from typing import Any, Callable

from .._service import SessionRecord
from ...message import Msg


class StorageError(Exception):
    """Structured failure for storage operations (corruption, version
    mismatch, serialization problems)."""


class StorageBase(ABC):
    """Persist sessions so they survive a process restart.

    Implementations store the session metadata plus the agent's
    conversation state; ``load_session`` rebuilds a live record via an
    agent factory supplied by the caller.
    """

    @abstractmethod
    async def save_session(self, record: SessionRecord) -> None:
        """Create or update the stored session from the record."""

    @abstractmethod
    async def load_session(
        self,
        session_id: str,
        agent_factory: Callable[[], Any] | None = None,
    ) -> SessionRecord:
        """Rebuild the stored session.

        Args:
            session_id (`str`):
                The session to restore.
            agent_factory (`Callable[[], Any] | None`, optional):
                Builds a fresh agent instance; the stored conversation
                state is injected into it. Required to get a usable
                record.
        """

    @abstractmethod
    async def append_message(self, session_id: str, msg: Msg) -> None:
        """Append one message to the stored conversation, atomically."""

    @abstractmethod
    async def close(self) -> None:
        """Release the storage resources."""
