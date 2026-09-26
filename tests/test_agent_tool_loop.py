"""Stage 4 agent reasoning-acting loop with the toolkit."""

import asyncio
import json

from agentscope.agent import Agent
from agentscope.message import (
    TextBlock,
    ToolCallBlock,
    ToolResultBlock,
    ToolResultState,
    UserMsg,
)
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.state import AgentState
from agentscope.tool import (
    FunctionTool,
    ToolBase,
    ToolChunk,
    Toolkit,
)


class AddTool(ToolBase):
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

    async def call(self, *, a: int, b: int) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _tool_call_response(call_id: str, a: int, b: int) -> ChatResponse:
    return ChatResponse(
        content=[
            ToolCallBlock(
                id=call_id,
                name="add",
                input=json.dumps({"a": a, "b": b}),
            ),
        ],
        is_last=True,
    )


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


def test_one_tool_round() -> None:
    model = FakeChatModel(
        [
            _tool_call_response("call-1", 2, 3),
            _text_response("The answer is 5"),
        ],
    )
    toolkit = Toolkit(tools=[AddTool()])
    agent = Agent("Friday", "Use tools when needed", model, toolkit=toolkit)

    reply = asyncio.run(agent.reply(UserMsg("Alice", "What is 2 + 3?")))

    # The final reply text is produced after the tool result round.
    assert reply.get_text_content() == "The answer is 5"
    assert reply.finished_reason == "completed"

    # One assistant message per reply, ordered tool_call -> tool_result -> text.
    assert [msg.role for msg in agent.state.context] == ["user", "assistant"]
    assistant = agent.state.context[-1]
    assert assistant.name == "Friday"
    block_types = [block.type for block in assistant.content]
    assert block_types == ["tool_call", "tool_result", "text"]

    tool_call, tool_result = assistant.content[0], assistant.content[1]
    assert isinstance(tool_call, ToolCallBlock)
    assert isinstance(tool_result, ToolResultBlock)
    assert tool_result.id == tool_call.id == "call-1"
    assert tool_result.name == "add"
    assert tool_result.state == ToolResultState.SUCCESS
    assert tool_result.output[0].text == "5"
    assert tool_call.state == "finished"

    # The second model call must have carried the tool schemas and the
    # tool result so the model can produce the final answer.
    assert len(model.calls) == 2
    second_messages, second_tools, _ = model.calls[1]
    assert second_tools is not None
    assert any(
        schema["function"]["name"] == "add" for schema in second_tools
    )
    assert [msg.role for msg in second_messages] == ["system", "user", "assistant"]
    result_blocks = second_messages[-1].get_content_blocks("tool_result")
    assert len(result_blocks) == 1
    assert result_blocks[0].output[0].text == "5"


def test_multiple_tool_calls_keep_request_order() -> None:
    first = ChatResponse(
        content=[
            ToolCallBlock(id="call-a", name="add", input=json.dumps({"a": 1, "b": 2})),
            ToolCallBlock(id="call-b", name="add", input=json.dumps({"a": 10, "b": 20})),
        ],
        is_last=True,
    )
    model = FakeChatModel([first, _text_response("done")])
    agent = Agent("Friday", "Prompt", model, toolkit=Toolkit(tools=[AddTool()]))

    asyncio.run(agent.reply(UserMsg("Alice", "Add twice")))

    assistant = agent.state.context[-1]
    results = [
        block for block in assistant.content if isinstance(block, ToolResultBlock)
    ]
    assert [result.id for result in results] == ["call-a", "call-b"]
    assert results[0].output[0].text == "3"
    assert results[1].output[0].text == "30"


def test_max_iters_stops_the_loop() -> None:
    # The model always requests another tool call; the loop must stop.
    model = FakeChatModel(
        [_tool_call_response(f"call-{i}", i, i) for i in range(10)],
    )
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        toolkit=Toolkit(tools=[AddTool()]),
        max_iters=3,
    )

    reply = asyncio.run(agent.reply(UserMsg("Alice", "Keep adding")))

    assert len(model.calls) == 3
    assert reply.finished_reason == "exceed_max_iters"
    results = [
        block for block in reply.content if isinstance(block, ToolResultBlock)
    ]
    assert [result.id for result in results] == ["call-0", "call-1", "call-2"]


def test_agent_without_toolkit_still_rejects_tool_calls() -> None:
    import pytest

    model = FakeChatModel([_tool_call_response("call-1", 1, 1)])
    agent = Agent("Friday", "Prompt", model)
    with pytest.raises(NotImplementedError, match="stage 4"):
        asyncio.run(agent.reply(UserMsg("Alice", "Hi")))


def test_agent_state_reuse_across_replies() -> None:
    model = FakeChatModel(
        [
            _tool_call_response("call-1", 2, 3),
            _text_response("first done"),
            _text_response("second done"),
        ],
    )
    state = AgentState()
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        state=state,
        toolkit=Toolkit(tools=[FunctionTool(func=lambda a, b: a + b, name="add")]),
    )
    asyncio.run(agent.reply(UserMsg("Alice", "What is 2 + 3?")))
    second = asyncio.run(agent.reply(UserMsg("Alice", "Thanks")))

    assert second.get_text_content() == "second done"
    assert [msg.role for msg in state.context] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
