# -*- coding: utf-8 -*-
"""The realtime model and transport contracts."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class RealtimeModelBase(ABC):
    """A realtime audio model: audio in, transcript and audio out."""

    @abstractmethod
    async def start(self) -> None:
        """Open the realtime session."""

    @abstractmethod
    async def send_audio(self, audio: str, seq: int = 0) -> None:
        """Send one chunk of user audio."""

    @abstractmethod
    def receive_events(self) -> AsyncGenerator:
        """Yield transcript/audio/interruption events as they arrive."""

    @abstractmethod
    async def interrupt(self) -> None:
        """Stop the current generation; old output is discarded."""

    @abstractmethod
    async def close(self) -> None:
        """Release the session; safe to call twice."""


class RealtimeTransportBase(ABC):
    """Carry realtime events between the agent and the model."""

    @abstractmethod
    async def send_model(self, event) -> None:
        """Push an event towards the model side."""

    @abstractmethod
    def receive(self) -> AsyncGenerator:
        """Yield events arriving from the model side."""

    @abstractmethod
    async def close(self) -> None:
        """Release the transport."""
