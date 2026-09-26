# -*- coding: utf-8 -*-
"""Session routing for channel events."""
from .._service import SessionService
from ._base import ChannelEvent


class ChannelRouter:
    """Map (channel_id, external_user_id) to one session.

    The same user on the same channel always lands in the same session;
    the same user on a different channel gets a separate one, so
    conversations never cross wires.
    """

    def __init__(self, sessions: SessionService) -> None:
        self._sessions = sessions
        self._routes: dict[str, str] = {}

    def resolve(self, event: ChannelEvent) -> str:
        key = self.route_key(event)
        if key not in self._routes:
            self._routes[key] = self._sessions.create(
                agent_id=event.channel_id,
            ).session_id
        return self._routes[key]

    @staticmethod
    def route_key(event: ChannelEvent) -> str:
        return f"{event.channel_id}:{event.external_user_id}"
