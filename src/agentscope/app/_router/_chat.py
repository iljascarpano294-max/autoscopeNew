# -*- coding: utf-8 -*-
"""HTTP routes for chatting with a session."""
from fastapi import APIRouter, HTTPException

from .._service import ChatService, SessionNotFound, SessionService
from ._schema import ChatReplyResponse, SendMessageRequest


def create_chat_router(sessions: SessionService, chat: ChatService) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/sessions/{session_id}/messages",
        response_model=ChatReplyResponse,
    )
    async def send_message(
        session_id: str,
        body: SendMessageRequest,
    ) -> ChatReplyResponse:
        try:
            reply = await chat.send(session_id, body.message)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail="session not found") from None
        except Exception:
            # Model and tool failures stay structured and generic: no
            # stack traces, no credentials, no fake assistant message.
            raise HTTPException(
                status_code=500,
                detail="the agent failed to reply",
            ) from None
        return ChatReplyResponse(
            session_id=session_id,
            message_id=reply.id,
            reply=reply.get_text_content() or "",
        )

    return router
