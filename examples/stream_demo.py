"""Stage 5 streaming demo: watch the reply arrive as events.

Data flow in this example (stage 5):

1. `Agent.reply_stream` yields ReplyStartEvent, then one ModelCallStartEvent
   per model call.
2. Each streamed ChatResponse delta from the model is converted into
   TextBlockStart/Delta/End events (empty deltas are dropped so no ghost
   text appears); the closing is_last chunk carries the full text and is
   persisted into the context exactly once.
3. When the model asks for a tool, ToolCallStart/Delta/End events stream the
   arguments, the toolkit executes it, and ToolResultStart/TextDelta/End
   events stream the result back.
4. ModelCallEndEvent closes each model call; ReplyEndEvent closes the reply
   and the final Msg object follows exactly once.

`print_stream` only renders events; it never touches agent state.
"""

import asyncio

from agentscope.agent import Agent
from agentscope.console import print_stream
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.tool import FunctionTool, Toolkit


async def main() -> None:
    def add(a: int, b: int) -> int:
        """Add two integers.

        Args:
            a: The first integer.
            b: The second integer.
        """
        return a + b

    model = FakeChatModel([
        [
            ChatResponse(
                content=[ToolCallBlock(id="call-1", name="add", input='{"a":')],
                is_last=False,
            ),
            ChatResponse(
                content=[
                    ToolCallBlock(id="call-1", name="add", input=' 2, "b": 3}'),
                ],
                is_last=False,
            ),
            ChatResponse(
                content=[
                    ToolCallBlock(
                        id="call-1",
                        name="add",
                        input='{"a": 2, "b": 3}',
                    ),
                ],
                is_last=True,
            ),
        ],
        [
            ChatResponse(
                content=[TextBlock(text="2 + 3 equals ", id="b1")],
                is_last=False,
            ),
            ChatResponse(
                content=[TextBlock(text="5.", id="b1")],
                is_last=False,
            ),
            ChatResponse(
                content=[TextBlock(text="2 + 3 equals 5.", id="b1")],
                is_last=True,
            ),
        ],
    ])
    toolkit = Toolkit(tools=[FunctionTool(func=add)])
    agent = Agent("Friday", "Use the add tool for arithmetic.", model, toolkit=toolkit)

    async for item in agent.reply_stream(UserMsg("Alice", "What is 2 + 3?")):
        print_stream([item])
    print(f"\nContext messages: {len(agent.state.context)}")


if __name__ == "__main__":
    asyncio.run(main())
