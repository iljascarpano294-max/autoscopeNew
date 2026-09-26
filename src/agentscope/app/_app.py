# -*- coding: utf-8 -*-
"""The agentscope app: sessions and chat over HTTP."""
from typing import Any, Callable

from fastapi import FastAPI

from ._lifespan import lifespan
from ._router import create_chat_router, create_session_router
from ._service import ChatService, SessionService


def create_app(agent_factory: Callable[[], Any]) -> FastAPI:
    """Build the FastAPI application around an agent factory.

    Args:
        agent_factory (`Callable[[], Any]`):
            Builds one agent instance per created session; inject a
            factory over a Fake model in tests.

    Returns:
        `FastAPI`:
            The app exposing POST/GET/DELETE /sessions and
            POST /sessions/{session_id}/messages.
    """
    sessions = SessionService(agent_factory)
    chat = ChatService(sessions)

    app = FastAPI(title="agentscope", lifespan=lifespan)
    app.state.sessions = sessions
    app.state.chat = chat

    app.include_router(create_session_router(sessions))
    app.include_router(create_chat_router(sessions, chat))
    return app
