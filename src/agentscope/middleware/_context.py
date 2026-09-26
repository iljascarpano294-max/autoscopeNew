# -*- coding: utf-8 -*-
"""Context compression middleware for AgentScope agents."""
from typing import TYPE_CHECKING, Callable

from .._utils._common import _execute_async_or_sync_func
from ..message import Msg, UserMsg
from ._base import MiddlewareBase

if TYPE_CHECKING:
    from ..agent import Agent
else:
    Agent = "Agent"  # noqa: N816


class ContextCompressionMiddleware(MiddlewareBase):
    """Compress the conversation history once it grows past a threshold.

    When ``len(context) > max_messages`` at the start of a reply, the
    oldest messages except the most recent ``keep_recent`` are replaced by
    a single summary message (role user, name ``context_summary``), so the
    system prompt (rebuilt per model call) and the latest exchange stay
    intact. Messages that are already summaries are never summarized
    again: their text is carried into the new summary verbatim, which
    keeps each batch of messages compressed exactly once.
    """

    def __init__(
        self,
        max_messages: int,
        keep_recent: int,
        summarize: Callable[[list[Msg]], str] | None = None,
        summary_name: str = "context_summary",
    ) -> None:
        """Initialize the compression middleware.

        Args:
            max_messages (`int`):
                Compression triggers only when the context holds more than
                this many messages.
            keep_recent (`int`):
                Number of most recent messages kept verbatim.
            summarize (`Callable[[list[Msg]], str] | None`, optional):
                Injected summary function (sync or async) receiving the
                messages to compress. Defaults to joining their text
                content, which keeps the data flow testable offline; a
                real summarizing model plugs in here.
            summary_name (`str`, optional):
                The name marking summary messages.
        """
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1.")
        if not 0 <= keep_recent < max_messages:
            raise ValueError(
                "keep_recent must be within [0, max_messages).",
            )
        self.max_messages = max_messages
        self.keep_recent = keep_recent
        self._summarize = summarize or self._default_summarize
        self.summary_name = summary_name

    async def on_reply(
        self,
        agent: Agent,
        input_kwargs: dict,
        next_handler: Callable,
    ):
        """Compress before the reply runs, then pass through unchanged."""
        await self._compress(agent)
        async for event in next_handler(**input_kwargs):
            yield event

    async def _compress(self, agent: Agent) -> None:
        context = agent.state.context
        if len(context) <= self.max_messages:
            return

        split = len(context) - self.keep_recent
        to_compress = context[:split]
        recent = context[split:]

        # Prior summaries are carried verbatim; each batch of messages is
        # summarized exactly once.
        summary_parts = [
            text
            for msg in to_compress
            if msg.name == self.summary_name
            and (text := msg.get_text_content())
        ]
        fresh = [
            msg for msg in to_compress if msg.name != self.summary_name
        ]
        if fresh:
            summary_parts.append(
                await _execute_async_or_sync_func(self._summarize, fresh),
            )

        summary_text = "\n".join(part for part in summary_parts if part)
        summary_msg = UserMsg(name=self.summary_name, content=summary_text)
        context[:] = [summary_msg, *recent]

    @staticmethod
    def _default_summarize(messages: list[Msg]) -> str:
        """Fallback summarizer: join the messages' text content."""
        texts = [
            text
            for msg in messages
            if (text := msg.get_text_content())
        ]
        return "\n".join(texts)
