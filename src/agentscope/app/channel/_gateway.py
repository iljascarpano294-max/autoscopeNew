# -*- coding: utf-8 -*-
"""The channel gateway: idempotent inbound dispatch and outbound retries."""
from dataclasses import dataclass

from .._service import ChatService, SessionService
from ._base import ChannelBase, ChannelEvent
from ._routing import ChannelRouter


@dataclass
class OutboundMessage:
    """One reply awaiting delivery, with its retry state."""

    channel_id: str
    target: str
    text: str
    status: str = "pending"
    """pending -> sent, or failed until a retry succeeds."""


class ChannelGateway:
    """Wire channels to sessions: normalize, dedupe, route, reply.

    Inbound, the gateway enforces the idempotency key before anything
    reaches the agent: a repeated webhook with the same message_id never
    triggers a second chat turn. Outbound failures are recorded with
    their retry state instead of being dropped.
    """

    def __init__(self, sessions: SessionService, chat: ChatService) -> None:
        self._sessions = sessions
        self._chat = chat
        self._router = ChannelRouter(sessions)
        self._seen_message_ids: set[str] = set()
        self._outbound: list[OutboundMessage] = []
        self._channels: dict[str, ChannelBase] = {}

    def register_channel(self, channel: ChannelBase) -> None:
        """Register a channel so its failed deliveries can be retried."""
        self._channels[channel.channel_id] = channel

    def resolve_session(self, event: ChannelEvent) -> str:
        return self._router.resolve(event)

    async def receive(self, event: ChannelEvent) -> str | None:
        """Handle one inbound event and return its session id.

        A duplicate message_id is acknowledged by returning the session
        without a new chat turn.
        """
        if event.message_id in self._seen_message_ids:
            return self._router.resolve(event)
        self._seen_message_ids.add(event.message_id)
        session_id = self._router.resolve(event)
        if event.text:
            await self._chat.send(session_id, event.text)
        return session_id

    async def send_reply(self, channel: ChannelBase, session_id: str, text: str) -> None:
        """Deliver a reply to the channel, keeping failures for retry."""
        self.register_channel(channel)
        outbound = OutboundMessage(
            channel_id=channel.channel_id,
            target=session_id,
            text=text,
        )
        try:
            await channel.send(outbound.target, outbound.text)
            outbound.status = "sent"
        except Exception:
            outbound.status = "failed"
        self._outbound.append(outbound)

    def pending_outbound(self) -> list[OutboundMessage]:
        """Messages that still need delivery, oldest first."""
        return [item for item in self._outbound if item.status != "sent"]

    async def retry_outbound(self) -> None:
        """Retry every failed delivery through its channel."""
        for item in self.pending_outbound():
            channel = self._channels.get(item.channel_id)
            if channel is None:
                continue
            try:
                await channel.send(item.target, item.text)
                item.status = "sent"
            except Exception:
                item.status = "failed"
