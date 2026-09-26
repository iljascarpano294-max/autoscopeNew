"""Stage 7 demo: custom middleware hooks and budget enforcement.

Hook timeline for one reply (registered order = entering order, exiting
in reverse):

    on_reply          wraps the entire reply stream
      on_compress...  (stage 7: ContextCompressionMiddleware runs on_reply)
      each reasoning round:
        on_reasoning    wraps the reasoning phase
          on_model_call wraps the raw model API call
      on_acting        wraps each raw toolkit.call_tool execution
    final Msg         yields after ReplyEndEvent

The demo also shows BudgetMiddleware(max_model_calls=1) stopping a reply
that needs a second model call, without calling the model again.
"""

import asyncio
import json

from agentscope.agent import Agent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.middleware import BudgetMiddleware, MiddlewareBase
from agentscope.tool import ToolBase, ToolChunk, Toolkit


class LoggingMiddleware(MiddlewareBase):
    """Record when each implemented hook is entered and exited."""

    def __init__(self, log: list) -> None:
        self.log = log

    async def on_reply(self, agent, input_kwargs, next_handler):
        self.log.append("on_reply:enter")
        async for item in next_handler(**input_kwargs):
            yield item
        self.log.append("on_reply:exit")

    async def on_model_call(self, agent, input_kwargs, next_handler):
        self.log.append("on_model_call:enter")
        result = await next_handler(**input_kwargs)
        self.log.append("on_model_call:exit")
        return result

    async def on_acting(self, agent, input_kwargs, next_handler):
        self.log.append(f"on_acting:enter({input_kwargs['tool_call'].name})")
        async for item in next_handler(**input_kwargs):
            yield item
        self.log.append("on_acting:exit")


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

    async def check_permissions(self, tool_input, context):
        from agentscope.permission import PermissionBehavior, PermissionDecision

        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="allowed",
        )

    async def call(self, *, a: int, b: int) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=str(a + b))])


def _tool_call_turn() -> ChatResponse:
    return ChatResponse(
        content=[
            ToolCallBlock(id="call-1", name="add", input=json.dumps({"a": 2, "b": 3})),
        ],
        is_last=True,
    )


async def main() -> None:
    # 1. A custom middleware records the hook order around one tool round.
    log = []
    model = FakeChatModel([_tool_call_turn(), ChatResponse(
        content=[TextBlock(text="2 + 3 equals 5")],
        is_last=True,
    )])
    agent = Agent(
        "Friday",
        "Use tools when needed.",
        model,
        toolkit=Toolkit(tools=[AddTool()]),
        middlewares=[LoggingMiddleware(log)],
    )
    reply = await agent.reply(UserMsg("Alice", "What is 2 + 3?"))
    print(f"reply: {reply.get_text_content()}")
    print("hooks:")
    for entry in log:
        print(f"  {entry}")

    # 2. The budget middleware blocks the second model call of a reply.
    budget = BudgetMiddleware(max_model_calls=1)
    budget_model = FakeChatModel([_tool_call_turn(), _tool_call_turn()])
    budget_agent = Agent(
        "Friday",
        "Prompt",
        budget_model,
        toolkit=Toolkit(tools=[AddTool()]),
        middlewares=[budget],
    )
    try:
        await budget_agent.reply(UserMsg("Alice", "add"))
    except RuntimeError as error:
        print(f"budget: {error}")
    print(f"budget: model calls made = {len(budget_model.calls)} (max 1)")


if __name__ == "__main__":
    asyncio.run(main())
