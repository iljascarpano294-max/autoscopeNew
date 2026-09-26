"""Model response containers independent of any provider API."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Self

from .._utils._common import _generate_id, _generate_timestamp
from .._utils._mixin import DictMixin
from ..message import DataBlock, TextBlock, ThinkingBlock, ToolCallBlock
from ._model_usage import ChatUsage


class FinishedReason(StrEnum):
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"


@dataclass
class ChatResponse(DictMixin):
    content: list[TextBlock | ToolCallBlock | ThinkingBlock | DataBlock]
    is_last: bool
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_generate_timestamp)
    type: Literal["chat_response"] = field(default_factory=lambda: "chat_response")
    usage: ChatUsage | None = field(default_factory=lambda: None)
    finished_reason: FinishedReason = field(default_factory=lambda: FinishedReason.COMPLETED)
    metadata: dict[str, Any] = field(default_factory=dict)

    def append_text(self, text: str, block_id: str | None = None) -> Self:
        for block in self.content:
            if isinstance(block, TextBlock) and (block_id is None or block.id == block_id):
                block.text += text
                return self
        self.content.append(TextBlock(text=text, id=block_id or _generate_id()))
        return self

    def append_tool_call(self, block_id: str, name: str, input: str) -> Self:
        for block in self.content:
            if isinstance(block, ToolCallBlock) and block.id == block_id:
                block.input += input
                return self
        self.content.append(ToolCallBlock(id=block_id, name=name, input=input))
        return self


@dataclass
class StructuredResponse:
    content: dict[str, Any]
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_generate_timestamp)
    type: Literal["structured_response"] = field(default_factory=lambda: "structured_response")
    usage: ChatUsage | None = field(default_factory=lambda: None)
