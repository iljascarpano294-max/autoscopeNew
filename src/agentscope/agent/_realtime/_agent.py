# -*- coding: utf-8 -*-
"""The realtime agent: audio in, transcript and audio out, interruptible."""
from ...realtime._base import RealtimeModelBase
from ...realtime._events import InterruptedEvent
from ._aggregator import RealtimeAggregator


class RealtimeAgent:
    """Drive one realtime model and aggregate its events.

    The agent owns the aggregator; `interrupt` drops pending playback
    and resets the turn, and `close` is idempotent so a dropped
    connection or a shutdown can both release the model resources.
    """

    def __init__(self, model: RealtimeModelBase) -> None:
        self.model = model
        self._aggregator = RealtimeAggregator()
        self._started = False
        self._closed = False

    async def start(self) -> None:
        await self.model.start()
        self._started = True

    async def send_audio(self, audio: str) -> RealtimeAggregator:
        """Send one user audio chunk and drain the model's response."""
        if not self._started:
            raise RuntimeError("The realtime agent is not started; call start() first.")
        await self.model.send_audio(audio)
        async for event in self.model.receive_events():
            self._aggregator.consume(event)
        return self._aggregator

    @property
    def transcript(self) -> str:
        return self._aggregator.transcript

    @property
    def audio_chunks(self) -> list[str]:
        return self._aggregator.audio_chunks

    async def interrupt(self) -> None:
        """Stop the current turn: old audio must not keep playing."""
        await self.model.interrupt()
        self._aggregator.consume(InterruptedEvent())

    async def close(self) -> None:
        """Release the model resources; safe to call twice."""
        if self._closed:
            return
        self._closed = True
        await self.model.close()
