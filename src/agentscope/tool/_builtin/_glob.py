# -*- coding: utf-8 -*-
"""The Glob tool: find files in the workspace by pattern."""
import asyncio
from typing import Any

from pydantic import BaseModel, Field

from ._common import WorkspaceTool
from .._response import ToolChunk

_MAX_MATCHES = 200


class _GlobParams(BaseModel):
    """Parameters of the Glob tool."""

    pattern: str = Field(description="A glob pattern such as '**/*.py', relative to the workspace root.")


class Glob(WorkspaceTool):
    """List files in the workspace matching a glob pattern."""

    name: str = "Glob"
    description: str = (
        "Find files inside the workspace matching a glob pattern, returned "
        "as relative paths sorted alphabetically."
    )
    input_schema: dict[str, Any] = _GlobParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = True

    async def call(self, pattern: str, **kwargs: Any) -> ToolChunk:
        root = self.workspace.root
        matches = sorted(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )
        if not matches:
            return self._ok(f"No files match '{pattern}'.")
        if len(matches) > _MAX_MATCHES:
            matches = matches[:_MAX_MATCHES] + [f"... (truncated at {_MAX_MATCHES})"]
        return self._ok("\n".join(matches))
