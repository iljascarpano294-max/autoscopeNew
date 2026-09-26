"""Stage 12 task 3: the SSE streaming route and message recovery."""

import asyncio
import json

import httpx

from agentscope.agent import Agent
from agentscope.app import create_app
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


def _factory() -> Agent:
    return Agent(
        "Friday",
        "Prompt",
        FakeChatModel(
            [
                ChatResponse(
                    content=[TextBlock(text="Hello, streamed world!")],
                    is_last=True,
                ),
            ],
        ),
    )


def test_sse_sequence() -> None:
    app = create_app(_factory)

    async def run():
        lines: list = []
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            session_id = created.json()["session_id"]

            async with client.stream(
                "GET",
                f"/sessions/{session_id}/events",
                params={"message": "hi"},
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith(("event:", "data:")):
                        lines.append(line)

            # A browser that disconnected can still pull the final message.
            recovered = await client.get(f"/sessions/{session_id}/messages")
            return lines, recovered.json()

    lines, recovered = _run(run())

    events = [line.split(":", 1)[1].strip() for line in lines if line.startswith("event:")]
    # Reply lifecycle: start ... end, and the reply message as its own event.
    assert events[0] == "REPLY_START"
    assert "TEXT_BLOCK_DELTA" in events
    assert events[-1] == "message"

    # The final text appears exactly once across the whole stream.
    data_frames = [line.split("data:", 1)[1].strip() for line in lines if line.startswith("data:")]
    streamed_text = " ".join(
        json.loads(frame).get("delta", "") for frame in data_frames if "delta" in json.loads(frame)
    )
    message_frames = [json.loads(frame) for frame in data_frames if "text" in json.loads(frame)]
    assert streamed_text == "Hello, streamed world!"
    assert message_frames[-1]["text"] == "Hello, streamed world!"

    # The recovery endpoint returns the same final message.
    assert recovered["reply"] == "Hello, streamed world!"


def _run(coro):
    return asyncio.run(coro)
