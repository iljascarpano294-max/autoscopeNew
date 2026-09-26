"""The A2A server process: expose one local agent over the loopback.

Run:  python examples/a2a_server.py --port 8765

The server binds to 127.0.0.1 only. POST /a2a accepts
``{"message_id", "text", "task_id"}`` and answers ``{"text": ...}``;
GET /health reports readiness. The demo agent uses a Fake model and
echoes the peer message, so no credentials are needed.
"""

import argparse

import uvicorn
from fastapi import FastAPI

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel

app = FastAPI(title="agentscope-a2a-server")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/a2a")
async def a2a(request: dict) -> dict:
    text = str(request.get("text", ""))
    # One agent per request keeps the demo stateless; a real deployment
    # plugs in its own agent factory and session handling here.
    agent = Agent(
        "Remote",
        "Echo the peer message.",
        FakeChatModel(
            [ChatResponse(content=[TextBlock(text=f"pong: {text}")], is_last=True)],
        ),
    )
    reply = await agent.reply(UserMsg(name="peer", content=text))
    return {"text": reply.get_text_content() or ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
