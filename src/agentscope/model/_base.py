"""Shared non-streaming chat model call wrapper for stage 2."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from ..message import Msg
from ._model_response import ChatResponse, FinishedReason


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
    ) -> ChatResponse:
        if self.stream:
            raise NotImplementedError("Streaming model calls arrive in stage 5.")
        for attempt in range(self.max_retries + 1):
            try:
                return await self._call_api(
                    self.model, messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
                )
            except asyncio.CancelledError:
                return ChatResponse(
                    content=[], is_last=True, finished_reason=FinishedReason.INTERRUPTED
                )
            except Exception as error:
                if not isinstance(error, self._get_retryable_exceptions()) or attempt == self.max_retries:
                    raise
                await asyncio.sleep(self.retry_delay)
        raise AssertionError("Unreachable retry state")

    @abstractmethod
    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Return one complete response from the provider."""
