# -*- coding: utf-8 -*-
"""The chat service: one serialized reply loop per session."""
import asyncio

from ...message import AssistantMsg, UserMsg
from ._session import SessionNotFound, SessionService


class ChatService:
    """Send user messages to a session's agent and return its replies.

    Each session gets its own asyncio.Lock, so concurrent requests for
    one session run strictly in acquisition order while different
    sessions proceed independently. The service never reimplements the
    reply loop: it delegates to the agent's own ``reply``. When the
    session service has durable storage, a completed turn is snapshotted
    afterwards — a failed model call never reaches storage.
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
        try:
            record = self._sessions.get(session_id)
        except SessionNotFound:
            # Not in memory (e.g. after a restart): restore from storage.
            record = await self._sessions.load(session_id)
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock

        async with lock:
            user_msg = UserMsg(name="user", content=message)
            reply = await record.agent.reply(user_msg)
            record.last_active_at = reply.finished_at or record.last_active_at
            # The turn is complete: only now does the state reach storage.
            await self._sessions.persist(record, [user_msg, reply])
        return reply
