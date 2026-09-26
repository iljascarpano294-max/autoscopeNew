"""Usage information returned by a chat model."""

from dataclasses import dataclass, field
from typing import Any, Literal

from .._utils._mixin import DictMixin


@dataclass
class ChatUsage(DictMixin):
    input_tokens: int
    output_tokens: int
    time: float
    cache_creation_input_tokens: int = field(default_factory=lambda: 0)
    cache_input_tokens: int = field(default_factory=lambda: 0)
    type: Literal["chat"] = field(default_factory=lambda: "chat")
    metadata: dict[str, Any] | None = field(default_factory=lambda: None)
