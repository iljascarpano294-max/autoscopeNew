# -*- coding: utf-8 -*-
"""Long-term memory middleware and backends."""
from typing import AsyncGenerator, Callable

from ...message import Msg, UserMsg
from .._base import MiddlewareBase
from ._base import LocalLongTermMemory, LongTermMemoryBackendBase


class LongTermMemoryMiddleware(MiddlewareBase):
    """Save and recall per-user facts across sessions.

    The middleware owns the memory backend so the Agent never depends on
    a database directly. Recalled facts are injected as a
    ``long_term_memory`` message before the user's own message; users
    with no matching facts see nothing injected, and facts never cross
    user boundaries.
    """

    def __init__(self, backend: LongTermMemoryBackendBase | None = None) -> None:
        self.backend = backend or LocalLongTermMemory()

    async def save(self, user_id: str, fact: str) -> None:
        await self.backend.save(user_id, fact)

    async def recall(self, user_id: str, query: str) -> list[str]:
        return await self.backend.recall(user_id, query)

    async def on_model_call(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable,
    ):
        messages: list[Msg] = input_kwargs.get("messages", [])
        user_id, query = self._last_user(messages)

        injected: list[Msg] | None = None
        if user_id is not None and query:
            facts = await self.backend.recall(user_id, query)
            if facts:
                text = "\n".join(f"- {fact}" for fact in facts)
                injected = [UserMsg(name="long_term_memory", content=text)]

        if injected is not None:
            last_user_index = max(
                index for index, msg in enumerate(messages) if msg.role == "user"
            )
            new_messages = [
                *messages[:last_user_index],
                *injected,
                *messages[last_user_index:],
            ]
            input_kwargs = {**input_kwargs, "messages": new_messages}

        return await next_handler(**input_kwargs)

    @staticmethod
    def _last_user(messages: list[Msg]) -> tuple[str | None, str | None]:
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.name, msg.get_text_content()
        return None, None
