"""Stage 10 task 3: the HTTP API around the session and chat services."""

import asyncio

import httpx
import pytest

from agentscope.agent import Agent
from agentscope.app import create_app
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


def _agent_factory():
    return Agent(
        "Friday",
        "Be concise",
        FakeChatModel(
            [ChatResponse(content=[TextBlock(text="hello from agent")], is_last=True)],
        ),
    )


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def _run(coro):
    return asyncio.run(coro)


def test_api_roundtrip() -> None:
    app = create_app(_agent_factory)

    async def run():
        async with _client(app) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            assert created.status_code == 201, created.text
            session_id = created.json()["session_id"]

            fetched = await client.get(f"/sessions/{session_id}")
            assert fetched.status_code == 200

            replied = await client.post(
                f"/sessions/{session_id}/messages",
                json={"message": "hi"},
            )
            assert replied.status_code == 200, replied.text

            listing = await client.get("/sessions/does-not-exist")
            assert listing.status_code == 404

            missing_message = await client.post(
                f"/sessions/{session_id}/messages",
                json={"message": ""},
            )
            return fetched.json(), replied.json(), missing_message.status_code

    fetched, replied, missing_status = _run(run())

    assert fetched["session_id"]
    assert fetched["agent_id"] == "demo"
    assert replied["reply"] == "hello from agent"
    # An empty message fails validation with 422.
    assert missing_status == 422


def test_empty_message_is_rejected_with_422() -> None:
    app = create_app(_agent_factory)

    async def run():
        async with _client(app) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            session_id = created.json()["session_id"]
            return await client.post(
                f"/sessions/{session_id}/messages",
                json={"message": ""},
            )

    response = _run(run())
    assert response.status_code == 422


def test_model_error_returns_structured_error() -> None:
    def factory():
        return Agent(
            "Friday",
            "Prompt",
            FakeChatModel([RuntimeError("model exploded")]),
        )

    app = create_app(factory)

    async def run():
        async with _client(app) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            session_id = created.json()["session_id"]
            return await client.post(
                f"/sessions/{session_id}/messages",
                json={"message": "hi"},
            )

    response = _run(run())
    assert response.status_code == 500
    # No stack trace or internals leak; the message is generic.
    assert "model exploded" not in response.text
    assert "Traceback" not in response.text


def test_responses_leak_no_credentials() -> None:
    app = create_app(_agent_factory)

    async def run():
        async with _client(app) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            session_id = created.json()["session_id"]
            await client.get(f"/sessions/{session_id}")
            replied = await client.post(
                f"/sessions/{session_id}/messages",
                json={"message": "hi"},
            )
            return created.json(), replied.json()

    created, replied = _run(run())
    for payload in (created, replied):
        assert "credential" not in payload
        assert "api_key" not in payload
        assert "sk-" not in str(payload)


def test_lifespan_releases_sessions_on_shutdown() -> None:
    app = create_app(_agent_factory)

    async def run():
        async with _client(app) as client, app.router.lifespan_context(app):
            created = await client.post("/sessions", json={"agent_id": "demo"})
            session_id = created.json()["session_id"]
            return session_id

    session_id = _run(run())

    # After shutdown the in-process sessions are gone: a new request sees
    # the session as unknown.
    app2 = app

    async def check():
        async with _client(app2) as client, app2.router.lifespan_context(app2):
            response = await client.get(f"/sessions/{session_id}")
            return response.status_code

    assert _run(check()) == 404
