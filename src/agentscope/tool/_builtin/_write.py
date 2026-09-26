# -*- coding: utf-8 -*-
"""The Write tool: create or overwrite a file inside the workspace."""
from typing import Any

from pydantic import BaseModel, Field

from ._common import WorkspaceTool
from .._response import ToolChunk


class _WriteParams(BaseModel):
    """Parameters of the Write tool."""

    file_path: str = Field(description="The path of the file to write, relative to the workspace root.")
    content: str = Field(description="The content to write into the file.")


class Write(WorkspaceTool):
    """Create or overwrite a text file in the workspace."""

    name: str = "Write"
    description: str = (
        "Create or overwrite a text file inside the workspace with the "
        "given content."
    )
    input_schema: dict[str, Any] = _WriteParams.model_json_schema()
    is_concurrency_safe: bool = False
    is_read_only: bool = False

    async def call(self, file_path: str, content: str, **kwargs: Any) -> ToolChunk:
        return await self._guarded(
            file_path,
            self._write(file_path, content),
        )

    async def _write(self, file_path: str, content: str) -> ToolChunk:
        await self.workspace.write(file_path, content)
        return self._ok(
            f"Written {len(content)} characters to '{file_path}'.",
        )
