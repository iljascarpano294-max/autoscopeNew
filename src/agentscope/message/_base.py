"""Messages exchanged by users, models, and agents."""

from typing import Any, Literal, Sequence, Self

from pydantic import BaseModel, Field, model_validator

from .._utils._common import _generate_id, _generate_timestamp
from ._block import (
    ContentBlock,
    ContentBlockTypes,
    DataBlock,
    TextBlock,
)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class Msg(BaseModel):
    name: str
    content: list[ContentBlock]
    role: Literal["user", "assistant", "system"]
    id: str = Field(default_factory=_generate_id)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_generate_timestamp)
    usage: Usage | None = None
    finished_at: str | None = None
    finished_reason: str | None = None
    structured_output: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_role_content(self) -> Self:
        if self.role == "user" and any(block.type not in ("text", "data") for block in self.content):
            raise ValueError("User message can only contain text blocks or data blocks.")
        if self.role == "system" and any(block.type != "text" for block in self.content):
            raise ValueError("System message can only contain text blocks.")
        return self

    def has_content_blocks(self, block_type: ContentBlockTypes | list[ContentBlockTypes] | None = None) -> bool:
        return bool(self.get_content_blocks(block_type))

    def get_text_content(self, separator: str = "\n") -> str | None:
        texts = [block.text for block in self.content if isinstance(block, TextBlock)]
        return separator.join(texts) if texts else None

    def get_content_blocks(
        self, block_type: ContentBlockTypes | list[ContentBlockTypes] | None = None
    ) -> Sequence[ContentBlock]:
        if block_type is None:
            return self.content
        types = [block_type] if isinstance(block_type, str) else block_type
        return [block for block in self.content if block.type in types]

    def append_usage(self, usage: Usage) -> Self:
        if self.usage is None:
            self.usage = usage.model_copy(deep=True)
        else:
            self.usage.input_tokens += usage.input_tokens
            self.usage.output_tokens += usage.output_tokens
            self.usage.cache_input_tokens += usage.cache_input_tokens
            self.usage.cache_creation_input_tokens += usage.cache_creation_input_tokens
        return self


def _to_blocks(content: str | list[ContentBlock]) -> list[ContentBlock]:
    return [TextBlock(text=content)] if isinstance(content, str) else content


def UserMsg(
    name: str,
    content: str | list[TextBlock | DataBlock],
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    finished_at: str | None = None,
    finished_reason: str | None = None,
    id: str | None = None,
) -> Msg:
    timestamp = created_at or _generate_timestamp()
    return Msg(
        name=name, content=_to_blocks(content), role="user", metadata=metadata or {},
        created_at=timestamp, finished_at=finished_at or timestamp,
        finished_reason=finished_reason, id=id or _generate_id(),
    )


def AssistantMsg(
    name: str,
    content: str | list[ContentBlock],
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    finished_at: str | None = None,
    structured_output: dict[str, Any] | None = None,
    finished_reason: str | None = None,
    id: str | None = None,
    usage: Usage | None = None,
) -> Msg:
    return Msg(
        name=name, content=_to_blocks(content), role="assistant", metadata=metadata or {},
        created_at=created_at or _generate_timestamp(), finished_at=finished_at,
        structured_output=structured_output, finished_reason=finished_reason,
        id=id or _generate_id(), usage=usage,
    )


def SystemMsg(
    name: str,
    content: str | list[TextBlock],
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    finished_at: str | None = None,
    finished_reason: str | None = None,
    id: str | None = None,
) -> Msg:
    timestamp = created_at or _generate_timestamp()
    return Msg(
        name=name, content=_to_blocks(content), role="system", metadata=metadata or {},
        created_at=timestamp, finished_at=finished_at or timestamp,
        finished_reason=finished_reason, id=id or _generate_id(),
    )
