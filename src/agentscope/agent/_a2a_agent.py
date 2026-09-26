# -*- coding: utf-8 -*-
"""The A2A agent: call a remote agent over an agent-to-agent protocol.

The remote is reached through a transport (an async callable receiving
the request dict and returning ``{"text": ..., "task_id": ...}``); the
default transport posts JSON to the peer endpoint. Idempotency (one
message id runs once), correlation ids and timeouts are enforced here,
before anything reaches the caller.
"""
import asyncio
from typing import Any, AsyncGenerator, Callable

from .._utils._common import _generate_id, _generate_timestamp
from ..event import AgentEvent, ReplyEndEvent, ReplyStartEvent
from ..message import AssistantMsg, Msg, TextBlock, UserMsg
from ..state import A2AState
from ..types import ErrorInfo, ReplyFinishedReason


class HttpTransport:
    """Default transport: POST the A2A request to the peer endpoint."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    async def __call__(self, request: dict) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.endpoint, json=request)
            response.raise_for_status()
            return response.json()


class A2AAgent:
    """Talk to a remote agent; shaped like an agent (reply_stream)."""

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30,
        transport: Callable[[dict], Any] | None = None,
        name: str = "a2a",
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.name = name
        self._transport = transport or HttpTransport(endpoint)
        self.state = A2AState(peer_endpoint=endpoint)

    def reply_stream(
        self,
        inputs: Msg | list[Msg] | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        return self._reply(inputs)

    def _extract(self, inputs: Msg | list[Msg] | None) -> tuple[str, str]:
        """Return (message_id, text) from the inputs."""
        if isinstance(inputs, Msg):
            message_id = inputs.id
            text = inputs.get_text_content() or ""
            return message_id, text
        if isinstance(inputs, list) and inputs:
            return self._extract(inputs[-1])
        # A direct text call still gets a unique id.
        return _generate_id(), ""

    async def _reply(
        self,
        inputs: Msg | list[Msg] | None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        message_id, text = self._extract(inputs)
        self.state.reply_id = _generate_id()
        yield ReplyStartEvent(reply_id=self.state.reply_id, name=self.name)

        replay = message_id in self.state.seen_message_ids
        if replay:
            reply_text = self.state.cached_replies[message_id]
        else:
            request = {
                "message_id": message_id,
                "text": text,
                "task_id": self.state.task_id,
            }
            try:
                response = await asyncio.wait_for(
                    self._transport(request),
                    self.timeout,
                )
            except asyncio.TimeoutError:
                # Terminate instead of hanging: the caller sees a failed
                # end and may retry with a fresh message id.
                yield ReplyEndEvent(
                    reply_id=self.state.reply_id,
                    finished_reason=ReplyFinishedReason.ERROR,
                    error=ErrorInfo(
                        type="connection",
                        message=f"A2A call to '{self.endpoint}' timed out "
                        f"after {self.timeout}s.",
                    ),
                )
                return
            reply_text = str(response.get("text", ""))
            self.state.seen_message_ids.add(message_id)
            self.state.cached_replies[message_id] = reply_text

        yield AssistantMsg(
            name=self.name,
            content=[TextBlock(text=reply_text)],
            finished_at=_generate_timestamp(),
            finished_reason=str(ReplyFinishedReason.COMPLETED),
        )
