# -*- coding: utf-8 -*-
"""HTTP routes for session lifecycle."""
from fastapi import APIRouter, HTTPException

from .._service import SessionNotFound, SessionService
from ._schema import CreateSessionRequest, SessionResponse


def create_session_router(sessions: SessionService) -> APIRouter:
    router = APIRouter()

    @router.post("/sessions", response_model=SessionResponse, status_code=201)
    async def create_session(body: CreateSessionRequest) -> SessionResponse:
        record = sessions.create(agent_id=body.agent_id)
        return SessionResponse(
            session_id=record.session_id,
            agent_id=record.agent_id,
            created_at=record.created_at,
            last_active_at=record.last_active_at,
        )

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str) -> SessionResponse:
        try:
            record = sessions.get(session_id)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail="session not found") from None
        return SessionResponse(
            session_id=record.session_id,
            agent_id=record.agent_id,
            created_at=record.created_at,
            last_active_at=record.last_active_at,
        )

    @router.delete("/sessions/{session_id}", status_code=204)
    async def delete_session(session_id: str) -> None:
        try:
            sessions.delete(session_id)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail="session not found") from None

    return router
