"""Inspect the message shape before any model or Agent exists."""

from agentscope.message import AssistantMsg, ToolCallBlock, UserMsg
from agentscope.model import ChatResponse


def main() -> None:
    user = UserMsg("Alice", "What's the weather?")
    call = ToolCallBlock(id="weather-1", name="get_weather", input='{"city":"Beijing"}')
    assistant = AssistantMsg("Friday", [call])
    response = ChatResponse(content=[], is_last=True).append_text("I'll check.")

    print(user.model_dump_json(indent=2))
    print(assistant.model_dump_json(indent=2))
    print(response.content[0].text)


if __name__ == "__main__":
    main()
