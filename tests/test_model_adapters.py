"""Stage 16 task 3: provider adapter contract (DeepSeek over Mock transport)."""

import asyncio
import json

import httpx
import pytest

from agentscope.credential import OpenAICredential
from agentscope.message import TextBlock, ToolCallBlock
from agentscope.model import ChatUsage


def _openai_completion(content: str) -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
    }


def _tool_call_completion() -> dict:
    return {
        "id": "chatcmpl-2",
        "object": "chat.completion",
        "created": 1700000001,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "add",
                                "arguments": json.dumps({"a": 2, "b": 3}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
    }


def _model(handler) -> object:
    from agentscope.model._deepseek import DeepSeekChatModel

    transport = httpx.MockTransport(handler)
    return DeepSeekChatModel(
        credential=OpenAICredential(
            api_key="sk-dummy-not-a-real-key",
            base_url="https://api.deepseek.com",
        ),
        model="deepseek-chat",
        client_kwargs={"http_client": httpx.AsyncClient(transport=transport)},
    )


def test_adapter_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        user_text = body["messages"][-1]["content"]
        if "tool" in user_text:
            return httpx.Response(200, json=_tool_call_completion())
        if "fail" in user_text:
            return httpx.Response(500, json={"error": {"message": "upstream down"}})
        return httpx.Response(200, json=_openai_completion(f"echo: {user_text}"))

    model = _model(handler)

    async def run():
        from agentscope.message import UserMsg

        text = await model([UserMsg("Alice", "hello deepseek")])
        tool = await model([UserMsg("Alice", "call the tool")])
        with pytest.raises(Exception):
            await model([UserMsg("Alice", "fail please")])
        return text, tool

    text, tool = asyncio.run(run())

    # Plain text round trip with usage.
    assert text.content[0].text == "echo: hello deepseek"
    assert isinstance(text.usage, ChatUsage)
    assert text.usage.input_tokens == 5
    assert text.usage.output_tokens == 7

    # Tool calls map to ToolCallBlock with id/name/arguments.
    assert isinstance(tool.content[0], ToolCallBlock)
    assert tool.content[0].name == "add"
    assert json.loads(tool.content[0].input) == {"a": 2, "b": 3}


def test_import_without_credentials() -> None:
    # Importing and constructing the adapter never reads a real key; the
    # key comes from the caller (environment in production).
    from agentscope.model._deepseek import DeepSeekChatModel

    model = DeepSeekChatModel(
        credential=OpenAICredential(
            api_key="sk-dummy",
            base_url="https://api.deepseek.com",
        ),
    )
    assert model.model == "deepseek-chat"
