"""Shared chat model call wrapper for stages 2-5."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from pydantic import BaseModel

from ..message import Msg
from ._model_response import ChatResponse, FinishedReason
from ._utils import _StreamAccumulator


class ChatModelBase(ABC):
    """Call a provider model with a bounded, provider-declared retry policy."""

    class Parameters(BaseModel):
        """Provider-specific subclasses can add parameters."""

    def __init__(
        self,
        credential: object | None,
        model: str,
        parameters: BaseModel | None = None,
        stream: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        context_size: int = 32768,
    ) -> None:
        if max_retries < 0 or retry_delay < 0:
            raise ValueError("Retry settings must be non-negative.")
        self.credential = credential
        self.model = model
        self.parameters = parameters or self.Parameters()
        self.stream = stream
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.context_size = context_size

    @classmethod
    def _get_retryable_exceptions(cls) -> tuple[type[Exception], ...]:
        return ()

    async def __call__(
        self,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse | AsyncGenerator[ChatResponse, None]:
        """Call the model. Streaming subclasses return an async generator of
        ChatResponse chunks; non-streaming subclasses return one response."""
        for attempt in range(self.max_retries + 1):
            try:
                res = await self._call_api(
                    self.model, messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
                )
                break
            except asyncio.CancelledError:
                return ChatResponse(
                    content=[], is_last=True, finished_reason=FinishedReason.INTERRUPTED
                )
            except Exception as error:
                if not isinstance(error, self._get_retryable_exceptions()) or attempt == self.max_retries:
                    raise
                await asyncio.sleep(self.retry_delay)

        if isinstance(res, ChatResponse):
            return res

        async def _stream() -> AsyncGenerator[ChatResponse, None]:
            # Wrap the provider stream: pass deltas through, absorb empty
            # "carrier" chunks that only propagate metadata, and fall back
            # to the accumulated response when the provider never sends a
            # closing chunk (mirrors the reference __call__ streaming
            # branch).
            yield_acc_res = True
            acc_res = _StreamAccumulator()
            try:
                async for chunk in res:
                    if not chunk.is_last:
                        acc_res.append_chat_response(chunk)
                        acc_res.id = chunk.id
                        # Empty-content deltas are "carrier" chunks used by
                        # subclasses to propagate usage / id metadata. We
                        # absorb their metadata but do not surface them to
                        # the consumer, which keeps the visible stream free
                        # of spurious empty deltas.
                        if not chunk.content:
                            continue
                    else:
                        yield_acc_res = False
                    yield chunk
            except asyncio.CancelledError:
                acc_res.finished_reason = FinishedReason.INTERRUPTED
                yield_acc_res = True

            if yield_acc_res:
                yield acc_res.build()

        return _stream()

    @abstractmethod
    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse | AsyncGenerator[ChatResponse, None]:
        """Return one complete response, or a stream of chunks, from the provider."""
