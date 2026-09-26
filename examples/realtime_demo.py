"""Stage 15 demo: an A2A round and an interruptible realtime voice turn.

Both halves run offline: the A2A half uses a mock transport (the two
process variant lives in examples/a2a_server.py + a2a_client.py), and
the realtime half uses a fake audio model, so no microphone or voice
API key is needed.
"""

import asyncio

from agentscope.agent import A2AAgent, RealtimeAgent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.realtime import RealtimeModelBase


class MockA2ATransport:
    async def __call__(self, request: dict) -> dict:
        return {"text": f"remote says: {request['text']}", "task_id": request["task_id"]}


class FakeRealtimeModel(RealtimeModelBase):
    """Transcribes the fake audio and answers with a fake audio chunk."""

    def __init__(self) -> None:
        self._outgoing: list = []
        self._interrupted = False
        self._closed = False

    async def start(self) -> None:
        pass

    async def send_audio(self, audio: str, seq: int = 0) -> None:
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


async def main() -> None:
    # --- A2A: call a peer agent ---
    peer = A2AAgent(endpoint="http://peer.example", transport=MockA2ATransport())
    final = None
    async for item in peer.reply_stream(UserMsg("Alice", "status?")):
        if item.__class__.__name__ == "Msg":
            final = item
    print(f"a2a reply: {final.get_text_content()}")

    # --- realtime: one voice turn ---
    agent = RealtimeAgent(model=FakeRealtimeModel())
    await agent.start()
    await agent.send_audio("audio-input-1")
    print(f"transcript: {agent.transcript}")
    print(f"audio out: {agent.audio_chunks}")

    # Interrupting drops the pending playback.
    await agent.interrupt()
    print(f"after interrupt: audio={agent.audio_chunks}")
    await agent.close()
    await agent.close()  # idempotent
    print("closed: ok")


if __name__ == "__main__":
    asyncio.run(main())
