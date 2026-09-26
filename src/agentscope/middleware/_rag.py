# -*- coding: utf-8 -*-
"""RAG middleware: retrieve relevant chunks before each model call."""
from typing import AsyncGenerator, Callable, TYPE_CHECKING

from ..message import Msg, UserMsg
from ._base import MiddlewareBase

if TYPE_CHECKING:
    from ..agent import Agent
    from ..model import ChatResponse

from ..rag import KnowledgeBase


class RAGMiddleware(MiddlewareBase):
    """Inject retrieved knowledge into every model call.

    Before the raw model call, the last user message is used as the
    retrieval query. When chunks match, a ``rag_context`` message is
    inserted before the original user message with citations; when
    nothing matches, no fake context is added and the messages pass
    through unchanged. Retrieved content is external data: it is
    truncated to ``max_context_chars`` and never replaces the user's
    own message.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        top_k: int = 3,
        max_context_chars: int = 4000,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.top_k = top_k
        self.max_context_chars = max_context_chars

    async def on_model_call(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable,
    ) -> "ChatResponse":
        messages: list[Msg] = input_kwargs.get("messages", [])
        query = self._last_user_text(messages)

        injected: list[Msg] | None = None
        if query:
            results = await self.knowledge_base.retrieve(query, top_k=self.top_k)
            if results:
                lines = [
                    f"[{result.chunk.source}#{result.chunk.chunk_id}] {result.chunk.text}"
                    for result in results
                ]
                context_text = "\n".join(lines)[: self.max_context_chars]
                injected = [UserMsg(name="rag_context", content=context_text)]

        if injected is not None:
            # Insert the context before the user's own message, keeping
            # the original message object untouched.
            last_user_index = max(
                index for index, msg in enumerate(messages) if msg.role == "user"
            )
            new_messages = [
                *messages[:last_user_index],
                *injected,
                *messages[last_user_index:],
            ]
            input_kwargs = {**input_kwargs, "messages": new_messages}

        return await next_handler(**input_kwargs)

    @staticmethod
    def _last_user_text(messages: list[Msg]) -> str | None:
        for msg in reversed(messages):
            if msg.role == "user":
                text = msg.get_text_content()
                return text or None
        return None
