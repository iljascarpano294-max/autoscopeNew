"""Two complete Agent turns without an API key or external service."""

import asyncio

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel


async def main() -> None:
    model = FakeChatModel([
        ChatResponse(content=[TextBlock(text="Hello, Alice.")], is_last=True),
        ChatResponse(content=[TextBlock(text="Goodbye, Alice.")], is_last=True),
    ])
    agent = Agent("Friday", "You are a concise assistant.", model)
    for prompt in ("Hi", "Bye"):
        reply = await agent.reply(UserMsg("Alice", prompt))
        print(f"Alice: {prompt}\nFriday: {reply.get_text_content()}")
    print(f"Conversation messages: {len(agent.state.context)}")


if __name__ == "__main__":
    asyncio.run(main())
