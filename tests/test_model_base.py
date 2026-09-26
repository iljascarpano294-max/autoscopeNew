"""The shared model call contract, without a provider API."""

import asyncio

import pytest

from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel, FinishedReason


def test_fake_model_returns_text_and_records_input() -> None:
    answer = ChatResponse(content=[TextBlock(text="Hello")], is_last=True)
    model = FakeChatModel([answer])
    prompt = UserMsg("Alice", "Hi")
    result = asyncio.run(model([prompt]))
    assert result is answer
    assert model.calls[0][0] == [prompt]


def test_fake_model_returns_tool_call_as_data() -> None:
    call = ToolCallBlock(id="call-1", name="weather", input='{"city":"Beijing"}')
    model = FakeChatModel([ChatResponse(content=[call], is_last=True)])
    response = asyncio.run(model([UserMsg("Alice", "Weather?")]))
    assert response.content[0].name == "weather"
    assert response.content[0].id == "call-1"


def test_retry_only_declared_errors() -> None:
    class RetryModel(FakeChatModel):
        @classmethod
        def _get_retryable_exceptions(cls) -> tuple[type[Exception], ...]:
            return (ValueError,)

    model = RetryModel(
        [ValueError("temporary"), ChatResponse(content=[TextBlock(text="ok")], is_last=True)],
        max_retries=1,
        retry_delay=0,
    )
    assert asyncio.run(model([UserMsg("A", "Hi")])).content[0].text == "ok"
    assert len(model.calls) == 2

    other = RetryModel([RuntimeError("fatal")], max_retries=3, retry_delay=0)
    with pytest.raises(RuntimeError, match="fatal"):
        asyncio.run(other([UserMsg("A", "Hi")]))
    assert len(other.calls) == 1


def test_cancelled_call_returns_interrupted_response() -> None:
    model = FakeChatModel([asyncio.CancelledError()])
    response = asyncio.run(model([UserMsg("A", "Hi")]))
    assert response.is_last
    assert response.finished_reason == FinishedReason.INTERRUPTED
