# -*- coding: utf-8 -*-
"""The process-local realtime transport: plain asyncio queues."""
import asyncio
from typing import AsyncGenerator


class InMemoryRealtimeTransport:
    """Deliver events in order inside one process.

    Used to verify event semantics offline; WebSocket and provider
    transports implement the same interface.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def send_model(self, event) -> None:
        if self._closed:
            raise RuntimeError("The realtime transport is closed.")
        await self._queue.put(event)

    async def receive(self) -> AsyncGenerator:
        while True:
            event = await self._queue.get()
            yield event

    async def close(self) -> None:
        self._closed = True
