"""Typed content blocks carried by messages and model responses."""

from enum import StrEnum
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer

from .._utils._common import _generate_id, _generate_timestamp


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str
    id: str = Field(default_factory=_generate_id)
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


class ThinkingBlock(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["thinking"] = "thinking"
    thinking: str
    id: str = Field(default_factory=_generate_id)
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


class Base64Source(BaseModel):
    type: Literal["base64"] = "base64"
    data: str
    media_type: str


class URLSource(BaseModel):
    type: Literal["url"] = "url"
    url: AnyUrl
    media_type: str

    @field_serializer("url")
    def serialize_url(self, url: AnyUrl) -> str:
        return str(url)


class DataBlock(BaseModel):
    type: Literal["data"] = "data"
    source: Base64Source | URLSource
    id: str = Field(default_factory=_generate_id)
    name: str | None = None
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


class HintBlock(BaseModel):
    type: Literal["hint"] = "hint"
    hint: str | list[TextBlock | DataBlock]
    id: str = Field(default_factory=_generate_id)
    source: str | None = None
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


class ToolCallState(StrEnum):
    PENDING = "pending"
    ASKING = "asking"
    ALLOWED = "allowed"
    SUBMITTED = "submitted"
    FINISHED = "finished"


class ToolCallBlock(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="allow")
    type: Literal["tool_call"] = "tool_call"
    id: str
    name: str
    input: str
    state: ToolCallState = ToolCallState.PENDING
    suggested_rules: list[Any] = Field(default_factory=list)
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


class ToolResultState(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    DENIED = "denied"
    RUNNING = "running"


class ToolResultBlock(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    type: Literal["tool_result"] = "tool_result"
    id: str
    name: str
    output: str | list[TextBlock | DataBlock]
    state: ToolResultState = ToolResultState.RUNNING
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_generate_timestamp)
    finished_at: str | None = None


ContentBlock: TypeAlias = Annotated[
    TextBlock | ThinkingBlock | HintBlock | ToolCallBlock | ToolResultBlock | DataBlock,
    Field(discriminator="type"),
]
ContentBlockTypes: TypeAlias = Literal[
    "text", "thinking", "hint", "tool_call", "tool_result", "data"
]
