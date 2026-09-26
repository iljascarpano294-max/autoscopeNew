"""Stage 15 task 4: the realtime agent with a fake audio model."""

import asyncio

from agentscope.agent import RealtimeAgent
from agentscope.realtime import RealtimeModelBase


class FakeRealtimeModel(RealtimeModelBase):
    """No audio devices: queue-based deterministic realtime model."""

    def __init__(self) -> None:
        self._incoming: list = []
        self._outgoing: list = []
        self._interrupted = False
        self._closed = False
        self._seq = 0

    async def start(self) -> None:
        self._started = True

    async def send_audio(self, audio: str, seq: int = 0) -> None:
        self._incoming.append(audio)
        from agentscope.realtime import AudioOutputEvent, TranscriptDeltaEvent

        self._outgoing.append(TranscriptDeltaEvent(seq=0, delta=f"heard: {audio}"))
        self._outgoing.append(AudioOutputEvent(seq=0, data=f"out-{audio}"))

    async def receive_events(self):
        events, self._outgoing = self._outgoing, []
        for event in events:
            if self._interrupted:
                break
            yield event

    async def interrupt(self) -> None:
        self._interrupted = True
        self._outgoing.clear()

    async def close(self) -> None:
        self._closed = True


def test_voice_roundtrip() -> None:
    async def run():
        model = FakeRealtimeModel()
        agent = RealtimeAgent(model=model)
        await agent.start()

        await agent.send_audio("audio-1")
        transcript = agent.transcript
        audio = agent.audio_chunks

        await agent.close()
        await agent.close()  # double close is safe
        return transcript, audio, model._closed

    transcript, audio, closed = asyncio.run(run())

    # One input audio triggered one transcript plus one audio output.
    assert transcript == "heard: audio-1"
    assert audio == ["out-audio-1"]
    assert closed is True


def test_interrupt_stops_old_playback() -> None:
    async def run():
        model = FakeRealtimeModel()
        agent = RealtimeAgent(model=model)
        await agent.start()

        await agent.send_audio("audio-1")
        await agent.interrupt()

        # After the interrupt the old output is dropped; the model stops
        # producing for the old turn.
        return agent.audio_chunks, agent.transcript

    audio, transcript = asyncio.run(run())
    assert audio == []
    assert transcript == ""
