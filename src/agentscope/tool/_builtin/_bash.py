# -*- coding: utf-8 -*-
"""The Bash tool: run a shell command inside the workspace root."""
import asyncio
import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from ._common import WorkspaceTool
from .._response import ToolChunk


class _BashParams(BaseModel):
    """Parameters of the Bash tool."""

    command: str = Field(description="The shell command to execute.")


class Bash(WorkspaceTool):
    """Execute a shell command with the workspace root as working directory.

    The command runs in a subprocess with a hard timeout and an output
    length limit; both produce structured error results instead of
    hanging or flooding the context.
    """

    name: str = "Bash"
    description: str = (
        "Run a shell command inside the workspace root and return its "
        "combined output."
    )
    input_schema: dict[str, Any] = _BashParams.model_json_schema()
    is_concurrency_safe: bool = False
    is_read_only: bool = False

    def __init__(self, workspace, timeout: float = 60, max_output_length: int = 10_000, **kwargs: Any) -> None:
        super().__init__(workspace=workspace, **kwargs)
        self.timeout = timeout
        self.max_output_length = max_output_length

    async def call(self, command: str, **kwargs: Any) -> ToolChunk:
        return await self._guarded(command, self._run(command))

    async def _run(self, command: str) -> ToolChunk:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(self.workspace.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return self._error(
                f"Command timed out after {self.timeout} seconds and was "
                f"killed: {command}",
            )

        output = stdout.decode("utf-8", errors="replace")
        if len(output) > self.max_output_length:
            output = (
                output[: self.max_output_length]
                + f"\n... [truncated at {self.max_output_length} characters]"
            )

        if process.returncode != 0:
            return self._error(
                f"Command exited with code {process.returncode}:\n{output}",
            )
        return self._ok(output or "(no output)")
