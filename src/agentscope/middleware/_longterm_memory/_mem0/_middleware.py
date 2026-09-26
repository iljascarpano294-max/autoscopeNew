# -*- coding: utf-8 -*-
"""The Mem0 adapter for long-term memory (optional).

Requires the ``mem0`` package and a configured service; without them the
constructor reports it in a readable error, and the plain Agent is
completely unaffected. The interface matches the local backend, so it
is a drop-in replacement.
"""
from typing import Any

from .._base import LongTermMemoryBackendBase


class Mem0LongTermMemoryMiddleware(LongTermMemoryBackendBase):
    """Store and recall user facts through Mem0."""

    def __init__(self, mem0_client: Any = None) -> None:
        try:
            import mem0  # noqa: F401
        except ImportError as error:
            raise Exception(
                "The Mem0 adapter needs the 'mem0' package installed and "
                "a configured Mem0 client; install it or use "
                "LocalLongTermMemory instead.",
            ) from error
        if mem0_client is None:
            raise Exception(
                "The mem0 adapter needs a configured Mem0 client (set its "
                "API key through your environment, never in code).",
            )
        self._client = mem0_client

    async def save(self, user_id: str, fact: str) -> None:
        await self._client.add([{"role": "user", "content": fact}], user_id=user_id)

    async def recall(self, user_id: str, query: str) -> list[str]:
        result = await self._client.search(query, user_id=user_id)
        return [item["memory"] for item in result]
