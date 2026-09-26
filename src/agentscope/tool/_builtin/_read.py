# -*- coding: utf-8 -*-
"""The Read tool: read a text file inside the workspace."""
from pydantic import BaseModel, Field
from typing import Any

from ._common import WorkspaceTool
from .._response import ToolChunk


class _ReadParams(BaseModel):
    """Parameters of the Read tool."""

    file_path: str = Field(description="The path of the file to read, relative to the workspace root.")


class Read(WorkspaceTool):
    """Read the content of a text file in the workspace."""

    name: str = "Read"
    description: str = (
        "Read a text file inside the workspace and return its content."
    )
    input_schema: dict[str, Any] = _ReadParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = True

    async def call(self, file_path: str, **kwargs: Any) -> ToolChunk:
        return await self._guarded(
            file_path,
            self._read(file_path),
        )

    async def _read(self, file_path: str) -> ToolChunk:
        content = await self.workspace.read(file_path)
        return self._ok(content)
