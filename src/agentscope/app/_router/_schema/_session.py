# -*- coding: utf-8 -*-
"""Request/response schemas for the session routes."""
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Body of POST /sessions."""

    agent_id: str = Field(min_length=1, description="Which agent definition to run.")


class SessionResponse(BaseModel):
    """A session as seen from the outside."""

    session_id: str
    agent_id: str
    created_at: str
    last_active_at: str
