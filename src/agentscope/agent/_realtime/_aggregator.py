# -*- coding: utf-8 -*-
"""Assemble realtime events into a transcript and playable audio."""
from ...realtime._events import (
    AudioOutputEvent,
    InterruptedEvent,
    TranscriptDeltaEvent,
)


class OutOfOrderEventError(Exception):
    """An event arrived out of sequence; the turn's stream is ambiguous."""


class RealtimeAggregator:
    """Consume realtime events and build the turn's transcript and audio.

    Sequence numbers must be contiguous per stream (transcript and audio
    count separately); a gap raises instead of guessing. After an
    interruption the pending output is dropped and late events of the old
    turn are discarded until the new turn restarts the sequence.
    """

    def __init__(self) -> None:
        self._transcript_parts: list[str] = []
        self._expected_transcript_seq = 0
        self._audio_chunks: list[str] = []
        self._expected_audio_seq = 0
        self._interrupted = False

    @property
    def transcript(self) -> str:
        return "".join(self._transcript_parts)

    @property
    def audio_chunks(self) -> list[str]:
        return list(self._audio_chunks)

    def consume(self, event) -> None:
        if isinstance(event, InterruptedEvent):
            self._interrupted = True
            self._audio_chunks.clear()
            self._transcript_parts.clear()
            self._expected_transcript_seq = 0
            self._expected_audio_seq = 0
            return

        if isinstance(event, TranscriptDeltaEvent):
            if self._interrupted:
                if event.seq != 0:
                    return  # late transcript of the interrupted turn
                self._interrupted = False  # a new turn begins
            if event.seq != self._expected_transcript_seq:
                raise OutOfOrderEventError(
                    f"Transcript event seq {event.seq} arrived out of "
                    f"order (expected {self._expected_transcript_seq}).",
                )
            self._transcript_parts.append(event.delta)
            self._expected_transcript_seq += 1

        elif isinstance(event, AudioOutputEvent):
            if self._interrupted:
                if event.seq != 0:
                    return  # old audio must not keep playing
                self._interrupted = False  # a new turn begins
            if event.seq != self._expected_audio_seq:
                raise OutOfOrderEventError(
                    f"Audio event seq {event.seq} arrived out of order "
                    f"(expected {self._expected_audio_seq}).",
                )
            self._audio_chunks.append(event.data)
            self._expected_audio_seq += 1
