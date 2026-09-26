"""One offline reasoning-acting round: model asks for a tool, the toolkit
executes it, the result is fed back, and the model answers.

Data flow in this example (stage 4):

1. FakeChatModel returns a ChatResponse holding a ToolCallBlock (add(2, 3)).
2. Agent._acting passes the ToolCallBlock to Toolkit.call_tool, which parses
   and validates the JSON arguments, executes the tool, and yields a final
   ToolResponse (id == the tool call id, state == success).
3. The agent converts the ToolResponse into a ToolResultBlock and appends it
   to the same assistant message as the tool call (merged by reply_id).
4. The agent calls the model again; the model now sees the tool result and
   answers with plain text.

Permission checks arrive in stage 6 and streaming tool events in stage 5;
the tool here runs synchronously and locally.
"""

import asyncio
import json

from agentscope.agent import Agent
from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.tool import FunctionTool, ToolChunk, Toolkit


async def main() -> None:
    def add(a: int, b: int) -> int:
        """Add two integers.

        Args:
            a: The first integer.
            b: The second integer.
        """
        return a + b

    model = FakeChatModel([
        ChatResponse(
            content=[
                ToolCallBlock(
                    id="call-demo-1",
                    name="add",
                    input=json.dumps({"a": 2, "b": 3}),
                ),
            ],
            is_last=True,
        ),
        ChatResponse(
            content=[TextBlock(text="The answer is 5")],
            is_last=True,
        ),
    ])
    toolkit = Toolkit(tools=[FunctionTool(func=add)])
    agent = Agent("Friday", "Use the add tool for arithmetic.", model, toolkit=toolkit)

    reply = await agent.reply(UserMsg("Alice", "What is 2 + 3?"))
    print(f"Alice: What is 2 + 3?")
    for block in reply.content:
        if isinstance(block, ToolCallBlock):
            print(
                f"[{block.type}] {block.name}({block.input}) state={block.state}",
            )
        else:
            output = getattr(block, "output", None)
            if output is not None:
                texts = [
                    item.text if hasattr(item, "text") else str(item)
                    for item in output
                ]
                print(
                    f"[{block.type}] id={block.id} state={block.state} "
                    f"output={''.join(texts)!r}",
                )
            else:
                print(f"[{block.type}] {block.text}")
    print(f"Friday: {reply.get_text_content()}")
    print(f"Context messages: {len(agent.state.context)}")


if __name__ == "__main__":
    asyncio.run(main())
