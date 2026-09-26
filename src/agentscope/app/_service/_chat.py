# -*- coding: utf-8 -*-
"""The chat service: one serialized reply loop per session."""
import asyncio

from ...message import AssistantMsg, UserMsg
from ._session import SessionService


class ChatService:
    """Send user messages to a session's agent and return its replies.

    Each session gets its own asyncio.Lock, so concurrent requests for
    one session run strictly in acquisition order while different
    sessions proceed independently. The service never reimplements the
    reply loop: it delegates to the agent's own ``reply``.
    """

    def __init__(self, sessions: SessionService) -> None:
        self._sessions = sessions
        self._locks: dict[str, asyncio.Lock] = {}

    async def send(self, session_id: str, message: str) -> AssistantMsg:
        """Append the message to the session and return the agent reply.

        Raises:
            `SessionNotFound`:
                If the session id is unknown.
            `Exception`:
                Model errors propagate unchanged; no fake assistant
                message is left in the context.
        """
        record = self._sessions.get(session_id)
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock

        async with lock:
            reply = await record.agent.reply(
                UserMsg(name="user", content=message),
            )
        record.last_active_at = reply.finished_at or record.last_active_at
        return reply
