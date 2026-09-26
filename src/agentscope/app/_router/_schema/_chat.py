# -*- coding: utf-8 -*-
"""Request/response schemas for the chat routes."""
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Body of POST /sessions/{session_id}/messages."""

    message: str = Field(min_length=1, description="The user message text.")


class ChatReplyResponse(BaseModel):
    """The agent's reply to one message."""

    session_id: str
    message_id: str
    reply: str
