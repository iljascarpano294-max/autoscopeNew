# -*- coding: utf-8 -*-
"""The Edit tool: replace text in a file inside the workspace."""
from typing import Any

from pydantic import BaseModel, Field

from ._common import WorkspaceTool
from .._response import ToolChunk
from ...workspace import WorkspaceError


class _EditParams(BaseModel):
    """Parameters of the Edit tool."""

    file_path: str = Field(description="The path of the file to edit, relative to the workspace root.")
    old_string: str = Field(description="The exact text to replace.")
    new_string: str = Field(description="The replacement text.")


class Edit(WorkspaceTool):
    """Replace the first occurrence of a text snippet in a workspace file."""

    name: str = "Edit"
    description: str = (
        "Replace the first occurrence of old_string with new_string in a "
        "text file inside the workspace."
    )
    input_schema: dict[str, Any] = _EditParams.model_json_schema()
    is_concurrency_safe: bool = False
    is_read_only: bool = False

    async def call(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        **kwargs: Any,
    ) -> ToolChunk:
        return await self._guarded(
            file_path,
            self._edit(file_path, old_string, new_string),
        )

    async def _edit(self, file_path: str, old_string: str, new_string: str) -> ToolChunk:
        content = await self.workspace.read(file_path)
        if old_string not in content:
            return self._error(
                f"old_string not found in '{file_path}'; the file content "
                f"is unchanged.",
            )
        updated = content.replace(old_string, new_string, 1)
        await self.workspace.write(file_path, updated)
        return self._ok(f"Replaced {len(old_string)} characters in '{file_path}'.")
