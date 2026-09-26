# -*- coding: utf-8 -*-
"""The process-local message bus."""
from typing import Any

from ._base import BusEvent, Handler, MessageBusBase


class InMemoryMessageBus(MessageBusBase):
    """One event id is delivered to subscribers once; unacked events stay
    pending and are re-dispatched on :meth:`redeliver`. Topics are fully
    isolated: a handler only ever sees events from its own topic."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = {}
        self._pending: dict[str, BusEvent] = {}
        self._acked: set[str] = set()

    async def publish(self, topic: str, event_id: str, payload: Any) -> None:
        if event_id in self._acked or event_id in self._pending:
            # Duplicate publish of an event we already delivered or are
            # still waiting to see acknowledged: never deliver twice.
            return
        event = BusEvent(topic=topic, event_id=event_id, payload=payload)
        self._pending[event_id] = event
        await self._dispatch(event)

    async def subscribe(self, topic: str, handler: Handler) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    async def ack(self, event_id: str) -> None:
        self._pending.pop(event_id, None)
        self._acked.add(event_id)

    async def redeliver(self) -> None:
        """Re-dispatch every pending (unacked) event to its subscribers."""
        for event in list(self._pending.values()):
            await self._dispatch(event)

    async def _dispatch(self, event: BusEvent) -> None:
        for handler in self._subscribers.get(event.topic, []):
            await handler(event)
