"""Stage 10 demo: the app service over an in-process ASGI round.

The app keeps sessions in process memory only: restarting the process
loses them and later lookups report not-found. No network is needed —
the demo drives the ASGI app directly through httpx.
"""

import asyncio

import httpx

from agentscope.agent import Agent
from agentscope.app import create_app
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


def agent_factory() -> Agent:
    return Agent(
        "Friday",
        "Be concise",
        FakeChatModel(
            [ChatResponse(content=[TextBlock(text="Hello from the agent.")], is_last=True)],
        ),
    )


async def main() -> None:
    app = create_app(agent_factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client, app.router.lifespan_context(app):
        created = await client.post("/sessions", json={"agent_id": "demo"})
        session_id = created.json()["session_id"]
        print(f"created session: {session_id}")

        replied = await client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "Hi"},
        )
        print(f"reply: {replied.json()['reply']}")

    # After shutdown the in-process sessions are released.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client, app.router.lifespan_context(app):
        gone = await client.get(f"/sessions/{session_id}")
        print(f"after restart: {gone.status_code} (session is gone)")


if __name__ == "__main__":
    asyncio.run(main())
