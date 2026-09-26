"""Stage 15 task 3: realtime event semantics and the audio aggregator."""

import asyncio

import pytest

from agentscope.realtime import (
    AudioOutputEvent,
    InMemoryRealtimeTransport,
    InterruptedEvent,
    RealtimeAggregator,
    TranscriptDeltaEvent,
)


def test_realtime_order() -> None:
    aggregator = RealtimeAggregator()

    # Two input audio chunks produce one transcript and ordered outputs.
    aggregator.consume(TranscriptDeltaEvent(seq=0, delta="Hello"))
    aggregator.consume(TranscriptDeltaEvent(seq=1, delta=" world"))
    aggregator.consume(AudioOutputEvent(seq=0, data="audio-0"))
    aggregator.consume(AudioOutputEvent(seq=1, data="audio-1"))

    assert aggregator.transcript == "Hello world"
    assert aggregator.audio_chunks == ["audio-0", "audio-1"]


def test_out_of_order_event_is_rejected() -> None:
    aggregator = RealtimeAggregator()
    aggregator.consume(TranscriptDeltaEvent(seq=0, delta="Hello"))

    with pytest.raises(Exception, match="order"):
        aggregator.consume(TranscriptDeltaEvent(seq=2, delta="gap"))


def test_interrupt_discards_old_output() -> None:
    aggregator = RealtimeAggregator()
    aggregator.consume(AudioOutputEvent(seq=0, data="old-audio"))

    aggregator.consume(InterruptedEvent(reason="user barge-in"))

    # Old audio is dropped after the interruption...
    assert aggregator.audio_chunks == []
    # ...and late events from the previous turn are discarded, not played.
    aggregator.consume(AudioOutputEvent(seq=1, data="late-old-audio"))
    assert aggregator.audio_chunks == []

    # A new turn (fresh sequence) records again.
    aggregator.consume(TranscriptDeltaEvent(seq=0, delta="new turn"))
    aggregator.consume(AudioOutputEvent(seq=0, data="new-audio"))
    assert aggregator.transcript == "new turn"
    assert aggregator.audio_chunks == ["new-audio"]


def test_local_transport_carries_events_in_order() -> None:
    async def run():
        transport = InMemoryRealtimeTransport()
        await transport.send_model(
            TranscriptDeltaEvent(seq=0, delta="Hello"),
        )
        await transport.send_model(AudioOutputEvent(seq=0, data="audio-0"))

        received = []
        async for event in transport.receive():
            received.append(event)
            if len(received) == 2:
                break
        await transport.close()
        return received

    received = asyncio.run(run())
    assert [event.__class__.__name__ for event in received] == [
        "TranscriptDeltaEvent",
        "AudioOutputEvent",
    ]
