# -*- coding: utf-8 -*-
"""The channel abstraction: events in, outbound messages out."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChannelEvent:
    """One inbound message from an external channel, normalized."""

    channel_id: str
    """Which channel the message came from (e.g. "mock", "feishu")."""

    external_user_id: str
    """The channel's own user identifier."""

    message_id: str
    """The channel's message identifier; the idempotency key."""

    text: str
    """The message text."""

    metadata: dict = field(default_factory=dict)
    """Channel-specific extras (chat ids, reply targets, ...)."""


class ChannelBase(ABC):
    """One external channel: normalize inbound events, deliver replies."""

    channel_id: str
    """Identifier used in routing and logging."""

    @abstractmethod
    async def send(self, target: str, text: str) -> None:
        """Deliver ``text`` to the outbound ``target`` (user/chat id).

        Raises on failure; the gateway records the message for retry.
        """
