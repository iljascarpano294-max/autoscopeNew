"""Call the stage 2 model abstraction without credentials or a network."""

import asyncio

from agentscope.message import TextBlock, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel


async def main() -> None:
    model = FakeChatModel([
        ChatResponse(content=[TextBlock(text="I'll check the weather.")], is_last=True),
        ChatResponse(
            content=[ToolCallBlock(id="weather-1", name="get_weather", input='{"city":"Beijing"}')],
            is_last=True,
        ),
    ])
    prompt = UserMsg("Alice", "What's the weather in Beijing?")
    first = await model([prompt])
    second = await model([prompt])
    print(first.content[0].text)
    print(f"Tool request: {second.content[0].name}({second.content[0].input})")


if __name__ == "__main__":
    asyncio.run(main())
