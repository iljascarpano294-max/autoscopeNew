# -*- coding: utf-8 -*-
"""HTTP routes for chatting with a session."""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ...message import Msg
from ...event import TextBlockDeltaEvent
from .._service import ChatService, SessionNotFound, SessionService
from ._schema import ChatReplyResponse, SendMessageRequest


def create_chat_router(sessions: SessionService, chat: ChatService) -> APIRouter:
    router = APIRouter()

    @router.get("/sessions/{session_id}/messages")
    async def get_messages(session_id: str) -> dict:
        """Recovery endpoint: the latest assistant reply for the session."""
        try:
            record = await sessions.load(session_id)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail="session not found") from None
        context = record.agent.state.context
        latest = None
        for msg in reversed(context):
            if msg.role == "assistant":
                latest = msg
                break
        if latest is None:
            raise HTTPException(status_code=404, detail="no reply yet")
        return {"session_id": session_id, "reply": latest.get_text_content() or ""}

    @router.get("/sessions/{session_id}/events")
    async def stream_events(session_id: str, message: str) -> StreamingResponse:
        """Stream one reply as server-sent events.

        Each frame carries the event id (for resume/replay bookkeeping)
        and a JSON payload; the final assistant message is the last frame.
        """
        try:
            await sessions.load(session_id)
        except SessionNotFound:
            raise HTTPException(status_code=404, detail="session not found") from None

        async def generate():
            async for item in chat.stream(session_id, message):
                if isinstance(item, Msg):
                    frame = {"text": item.get_text_content() or ""}
                    yield f"event: message\ndata: {json.dumps(frame)}\n\n"
                else:
                    data: dict = {"id": item.id}
                    if isinstance(item, TextBlockDeltaEvent):
                        data["delta"] = item.delta
                    yield f"event: {item.type}\ndata: {json.dumps(data)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

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
