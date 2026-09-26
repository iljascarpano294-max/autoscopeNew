# -*- coding: utf-8 -*-
"""The DeepSeek chat adapter (OpenAI-compatible Chat Completions)."""
from typing import Any

from ...formatter import OpenAIChatFormatter
from ...message import Msg
from .._base import ChatModelBase
from .._model_response import ChatResponse
from .._openai_chat import OpenAIChatModel
from ._credential import DeepSeekCredential


class DeepSeekChatModel(OpenAIChatModel):
    """Call DeepSeek's OpenAI-compatible Chat Completions API.

    Inherits the stage-2 adapter semantics (text, tool calls, usage,
    streaming through the shared ``__call__`` wrapper); the credential
    defaults the base URL to the DeepSeek endpoint. The API key comes
    from the caller — importing or constructing this class never reads a
    real credential.
    """

    def __init__(
        self,
        credential: DeepSeekCredential,
        model: str = "deepseek-chat",
        parameters: ChatModelBase.Parameters | None = None,
        stream: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        context_size: int = 64000,
        formatter: OpenAIChatFormatter | None = None,
        client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            credential=credential,
            model=model,
            parameters=parameters,
            stream=stream,
            max_retries=max_retries,
            retry_delay=retry_delay,
            context_size=context_size,
            formatter=formatter,
            client_kwargs=client_kwargs,
        )

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        return await super()._call_api(
            model_name,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            **kwargs,
        )
