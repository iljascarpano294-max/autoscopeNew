"""OpenAI adapter requests and response mapping, with no network."""

import json
import asyncio

import httpx

from agentscope.credential import OpenAICredential
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import OpenAIChatModel


def test_chat_adapter_maps_text_and_tool_call() -> None:
    captured: list[dict] = []

    def respond(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-test",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Checking",
                        "tool_calls": [{
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "weather", "arguments": '{"city":"Beijing"}'},
                        }],
                    },
                    "finish_reason": "tool_calls",
                }],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
            },
        )

    async def run_request():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = OpenAIChatModel(
                credential=OpenAICredential(api_key="test-key", base_url="https://mock.local/v1"),
                model="gpt-test",
                stream=False,
                client_kwargs={"http_client": client},
            )
            return await model(
                [UserMsg("Alice", "Weather in Beijing?")],
                tools=[{"type": "function", "function": {"name": "weather", "parameters": {"type": "object"}}}],
            )

    response = asyncio.run(run_request())

    assert captured[0]["messages"] == [{"role": "user", "content": "Weather in Beijing?"}]
    assert captured[0]["tools"][0]["function"]["name"] == "weather"
    assert isinstance(response.content[0], TextBlock)
    assert response.content[0].text == "Checking"
    assert isinstance(response.content[1], ToolCallBlock)
    assert response.content[1].id == "call-1"
    assert response.content[1].name == "weather"
    assert response.content[1].input == '{"city":"Beijing"}'
    assert response.usage.input_tokens == 3


def test_credential_hides_api_key() -> None:
    credential = OpenAICredential(api_key="secret")
    assert "secret" not in repr(credential)
