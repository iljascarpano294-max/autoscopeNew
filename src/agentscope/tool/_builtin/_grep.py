# -*- coding: utf-8 -*-
"""The Grep tool: search file contents inside the workspace."""
import re
from typing import Any

from pydantic import BaseModel, Field

from ._common import WorkspaceTool
from .._response import ToolChunk
from ...message import TextBlock, ToolResultState

_MAX_RESULTS = 200
_MAX_LINE_LENGTH = 240


class _GrepParams(BaseModel):
    """Parameters of the Grep tool."""

    pattern: str = Field(description="A Python regular expression to search for in file contents.")


class Grep(WorkspaceTool):
    """Search the text files in the workspace for a regular expression."""

    name: str = "Grep"
    description: str = (
        "Search all text files inside the workspace for a regular "
        "expression and report 'path:line: text' matches."
    )
    input_schema: dict[str, Any] = _GrepParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = True

    async def call(self, pattern: str, **kwargs: Any) -> ToolChunk:
        try:
            regex = re.compile(pattern)
        except re.error as error:
            return self._error(f"Invalid regular expression '{pattern}': {error}")

        root = self.workspace.root
        results = []
        try:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # Binary files are skipped, not fatal.
                    continue
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if regex.search(line):
                        results.append(
                            f"{path.relative_to(root).as_posix()}:"
                            f"{line_number}: {line[:_MAX_LINE_LENGTH]}",
                        )
                        if len(results) >= _MAX_RESULTS:
                            results.append(f"... (truncated at {_MAX_RESULTS})")
                            break
                if len(results) >= _MAX_RESULTS:
                    break
        except OSError as error:
            return self._error(f"Search failed: {error}")

        if not results:
            return self._ok(f"No matches for '{pattern}'.")
        return self._ok("\n".join(results))
