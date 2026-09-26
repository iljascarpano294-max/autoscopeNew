"""Non-streaming OpenAI Chat Completions adapter for stage 2."""

from time import monotonic
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from ...credential import OpenAICredential
from ...formatter import OpenAIChatFormatter
from ...message import Msg, TextBlock, ToolCallBlock
from .._base import ChatModelBase
from .._model_response import ChatResponse
from .._model_usage import ChatUsage


class OpenAIChatModel(ChatModelBase):
    class Parameters(BaseModel):
        temperature: float | None = None
        max_tokens: int | None = None

    def __init__(
        self,
        credential: OpenAICredential,
        model: str,
        parameters: "OpenAIChatModel.Parameters | None" = None,
        stream: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        context_size: int = 128000,
        formatter: OpenAIChatFormatter | None = None,
        client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            credential=credential, model=model, parameters=parameters or self.Parameters(),
            stream=stream, max_retries=max_retries, retry_delay=retry_delay,
            context_size=context_size,
        )
        self.formatter = formatter or OpenAIChatFormatter()
        self.client = AsyncOpenAI(
            api_key=credential.api_key.get_secret_value(),
            base_url=credential.base_url,
            organization=credential.organization,
            max_retries=0,
            **(client_kwargs or {}),
        )

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        request: dict[str, Any] = {
            "model": model_name,
            "messages": self.formatter.format(messages),
            "stream": False,
        }
        request.update(self.parameters.model_dump(exclude_none=True))
        if tools is not None:
            request["tools"] = tools
        if tool_choice is not None:
            request["tool_choice"] = tool_choice
        request.update(kwargs)

        started = monotonic()
        raw = await self.client.chat.completions.create(**request)
        if not raw.choices:
            raise ValueError("OpenAI returned no choices.")
        message = raw.choices[0].message
        content: list[TextBlock | ToolCallBlock] = []
        if message.content:
            content.append(TextBlock(text=message.content))
        for call in message.tool_calls or []:
            content.append(
                ToolCallBlock(id=call.id, name=call.function.name, input=call.function.arguments)
            )
        usage = None
        if raw.usage is not None:
            usage = ChatUsage(
                input_tokens=raw.usage.prompt_tokens,
                output_tokens=raw.usage.completion_tokens,
                time=monotonic() - started,
            )
        return ChatResponse(content=content, is_last=True, id=raw.id, usage=usage)
