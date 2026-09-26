"""Convert stage 1 messages to OpenAI Chat Completions messages."""

from ..message import Msg, TextBlock, ToolCallBlock


class OpenAIChatFormatter:
    supported_input_media_types: list[str] = []

    def format(self, messages: list[Msg]) -> list[dict]:
        formatted: list[dict] = []
        for message in messages:
            blocks = message.content
            unsupported = [block.type for block in blocks if not isinstance(block, (TextBlock, ToolCallBlock))]
            if unsupported:
                raise ValueError(f"Unsupported content blocks for stage 2: {unsupported}")
            texts = [block.text for block in blocks if isinstance(block, TextBlock)]
            entry: dict = {"role": message.role, "content": "\n".join(texts)}
            calls = [block for block in blocks if isinstance(block, ToolCallBlock)]
            if calls:
                if message.role != "assistant":
                    raise ValueError("Only assistant messages may contain tool calls.")
                entry["tool_calls"] = [
                    {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": call.input}}
                    for call in calls
                ]
            formatted.append(entry)
        return formatted
