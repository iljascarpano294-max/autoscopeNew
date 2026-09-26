"""Stage 4 toolkit: registration, argument validation and dispatch."""

import asyncio
import json

import pytest

from agentscope.message import TextBlock, ToolCallBlock, ToolResultState
from agentscope.state import AgentState
from agentscope.tool import (
    FunctionTool,
    ToolBase,
    ToolChunk,
    Toolkit,
    ToolResponse,
)


class AddTool(ToolBase):
    """A deterministic tool with explicit schema and call counter."""

    name = "add"
    description = "Add two integers."
    input_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["a", "b"],
    }
    is_concurrency_safe = True
    is_read_only = True

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.executions = 0

    async def call(self, *, a: int, b: int) -> ToolChunk:
        self.executions += 1
        return ToolChunk(content=[TextBlock(text=str(a + b))])


class ExplodingTool(ToolBase):
    name = "explode"
    description = "Always raises."
    input_schema = {"type": "object", "properties": {}}
    is_concurrency_safe = True
    is_read_only = True

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.executions = 0

    async def call(self) -> ToolChunk:
        self.executions += 1
        raise ValueError("boom")


class StateTool(ToolBase):
    name = "peek_state"
    description = "Reports whether agent state was injected."
    input_schema = {"type": "object", "properties": {}}
    is_concurrency_safe = True
    is_read_only = True
    is_state_injected = True

    async def call(self, _agent_state: AgentState | None = None) -> ToolChunk:
        size = len(_agent_state.context) if _agent_state is not None else -1
        return ToolChunk(content=[TextBlock(text=f"context={size}")])


async def _run(toolkit: Toolkit, tool_call: ToolCallBlock, state=None):
    chunks, response = [], None
    async for item in toolkit.call_tool(tool_call, state or AgentState()):
        if isinstance(item, ToolResponse):
            response = item
        else:
            chunks.append(item)
    return chunks, response


def test_get_tool_schemas_shape() -> None:
    empty = _sync_schemas(Toolkit())
    assert empty == []

    toolkit = Toolkit(tools=[AddTool(), ExplodingTool()])
    schemas = _sync_schemas(toolkit)
    assert schemas == [
        {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two integers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["a", "b"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "explode",
                "description": "Always raises.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


def _sync_schemas(toolkit: Toolkit) -> list[dict]:
    return asyncio.run(toolkit.get_tool_schemas())


def test_dispatch_success() -> None:
    tool = AddTool()
    toolkit = Toolkit(tools=[tool])
    call = ToolCallBlock(id="call-1", name="add", input=json.dumps({"a": 2, "b": 3}))

    chunks, response = asyncio_run_run(toolkit, call)

    assert tool.executions == 1
    assert len(chunks) == 1
    assert chunks[0].content[0].text == "5"
    assert response.id == "call-1"
    assert response.state == ToolResultState.SUCCESS
    assert response.content[0].text == "5"


def asyncio_run_run(toolkit: Toolkit, call: ToolCallBlock, state=None):
    return asyncio.run(_run(toolkit, call, state))


def test_unknown_tool_returns_error_result() -> None:
    toolkit = Toolkit(tools=[AddTool()])
    call = ToolCallBlock(id="call-x", name="missing_tool", input="{}")

    chunks, response = asyncio_run_run(toolkit, call)

    assert response.state == ToolResultState.ERROR
    assert "ToolNotFoundError" in chunks[0].content[0].text
    assert "missing_tool" in chunks[0].content[0].text


def test_invalid_json_does_not_execute_tool() -> None:
    tool = AddTool()
    toolkit = Toolkit(tools=[tool])
    call = ToolCallBlock(id="call-2", name="add", input="not-a-json-object")

    chunks, response = asyncio_run_run(toolkit, call)

    assert tool.executions == 0
    assert response.state == ToolResultState.ERROR
    assert chunks[-1].state == ToolResultState.ERROR


def test_missing_required_argument_does_not_execute_tool() -> None:
    tool = AddTool()
    toolkit = Toolkit(tools=[tool])
    call = ToolCallBlock(id="call-3", name="add", input=json.dumps({"a": 2}))

    chunks, response = asyncio_run_run(toolkit, call)

    assert tool.executions == 0
    assert response.state == ToolResultState.ERROR
    assert "b" in chunks[0].content[0].text


def test_tool_exception_becomes_error_result() -> None:
    tool = ExplodingTool()
    toolkit = Toolkit(tools=[tool])
    call = ToolCallBlock(id="call-4", name="explode", input="{}")

    chunks, response = asyncio_run_run(toolkit, call)

    assert tool.executions == 1
    assert response.state == ToolResultState.ERROR
    assert "boom" in chunks[0].content[0].text


def test_repeated_tool_call_id_keeps_results_independent() -> None:
    toolkit = Toolkit(tools=[AddTool()])
    first = ToolCallBlock(id="same-id", name="add", input=json.dumps({"a": 1, "b": 2}))
    second = ToolCallBlock(id="same-id", name="add", input=json.dumps({"a": 5, "b": 6}))

    chunks_1, response_1 = asyncio_run_run(toolkit, first)
    chunks_2, response_2 = asyncio_run_run(toolkit, second)

    assert response_1.content[0].text == "3"
    assert response_2.content[0].text == "11"
    assert response_1.id == response_2.id == "same-id"
    assert chunks_1[0].content[0].text == "3"
    assert chunks_2[0].content[0].text == "11"


def test_duplicate_registration_overrides_by_name() -> None:
    first = AddTool()
    second = AddTool()
    toolkit = Toolkit(tools=[first])
    asyncio.run(toolkit.add_tool(second))

    schemas = _sync_schemas(toolkit)
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "add"

    call = ToolCallBlock(id="call-5", name="add", input=json.dumps({"a": 4, "b": 4}))
    _, response = asyncio_run_run(toolkit, call)
    assert response.content[0].text == "8"
    assert first.executions == 0
    assert second.executions == 1


def test_state_injection_passes_agent_state() -> None:
    toolkit = Toolkit(tools=[StateTool()])
    state = AgentState()
    call = ToolCallBlock(id="call-6", name="peek_state", input="{}")

    chunks, response = asyncio_run_run(toolkit, call, state)

    assert response.state == ToolResultState.SUCCESS
    assert chunks[0].content[0].text == "context=0"


def test_function_tool_sync_function() -> None:
    def add(a: int, b: int) -> int:
        """Add two integers.

        Args:
            a: The first integer.
            b: The second integer.
        """
        return a + b

    toolkit = Toolkit(tools=[FunctionTool(func=add)])
    schema = _sync_schemas(toolkit)[0]["function"]
    assert schema["name"] == "add"
    assert schema["description"] == "Add two integers."
    assert set(schema["parameters"]["properties"]) == {"a", "b"}
    assert schema["parameters"]["required"] == ["a", "b"]
    assert "title" not in schema["parameters"]

    call = ToolCallBlock(id="call-7", name="add", input=json.dumps({"a": 20, "b": 22}))
    chunks, response = asyncio_run_run(toolkit, call)
    assert response.state == ToolResultState.SUCCESS
    assert response.content[0].text == "42"


def test_function_tool_async_function_and_json_result() -> None:
    async def get_weather(location: str) -> dict:
        """Get the weather.

        Args:
            location: The city name.
        """
        return {"city": location, "temperature": 25}

    toolkit = Toolkit(tools=[FunctionTool(func=get_weather)])
    call = ToolCallBlock(
        id="call-8",
        name="get_weather",
        input=json.dumps({"location": "Hangzhou"}),
    )
    chunks, response = asyncio_run_run(toolkit, call)
    assert response.state == ToolResultState.SUCCESS
    assert json.loads(response.content[0].text) == {
        "city": "Hangzhou",
        "temperature": 25,
    }


def test_invalid_input_schema_rejected_at_registration() -> None:
    class BadTool(ToolBase):
        name = "bad"
        description = "Bad schema."
        input_schema = {"type": "string"}

        async def call(self) -> ToolChunk:
            return ToolChunk(content=[])

    with pytest.raises(ValueError, match="Invalid input_schema"):
        Toolkit(tools=[BadTool()])
