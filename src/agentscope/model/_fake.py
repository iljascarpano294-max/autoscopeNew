"""A deterministic model for examples and offline tests."""

from typing import Any

from ..message import Msg
from ._base import ChatModelBase
from ._model_response import ChatResponse


class FakeChatModel(ChatModelBase):
    def __init__(
        self,
        responses: list[ChatResponse | BaseException],
        max_retries: int = 0,
        retry_delay: float = 0,
    ) -> None:
        super().__init__(
            credential=None, model="fake", stream=False,
            max_retries=max_retries, retry_delay=retry_delay,
        )
        self.responses = list(responses)
        self.calls: list[tuple[list[Msg], list[dict] | None, str | None]] = []

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.calls.append((list(messages), tools, tool_choice))
        if not self.responses:
            raise RuntimeError("FakeChatModel has no response left.")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response
