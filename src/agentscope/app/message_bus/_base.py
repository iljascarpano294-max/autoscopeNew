# -*- coding: utf-8 -*-
"""The message bus contract."""
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


class BusEvent:
    """One event on the bus."""

    __slots__ = ("topic", "event_id", "payload")

    def __init__(self, topic: str, event_id: str, payload: Any) -> None:
        self.topic = topic
        self.event_id = event_id
        self.payload = payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"BusEvent(topic={self.topic!r}, event_id={self.event_id!r})"


Handler = Callable[[BusEvent], Awaitable[None]]


class MessageBusBase(ABC):
    """Publish events to topics and consume them with at-least-once
    delivery plus event-id based de-duplication.

    A consumer acknowledges an event with ``ack``; unacked events may be
    redelivered (retry semantics), so handlers must tolerate duplicates
    or rely on the bus's per-event-id dedup — a non-idempotent tool must
    never run twice for one event id.
    """

    @abstractmethod
    async def publish(self, topic: str, event_id: str, payload: Any) -> None:
        """Publish one event; duplicates of a known event id are dropped."""

    @abstractmethod
    async def subscribe(self, topic: str, handler: Handler) -> None:
        """Register a handler for a topic."""

    @abstractmethod
    async def ack(self, event_id: str) -> None:
        """Mark the event as processed; redelivery stops."""
