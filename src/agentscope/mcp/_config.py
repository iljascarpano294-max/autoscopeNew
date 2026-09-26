# -*- coding: utf-8 -*-
"""The MCP client configuration models."""
from pydantic import BaseModel, Field


class StdioMCPConfig(BaseModel):
    """Configuration for a local MCP server launched over stdio."""

    command: str
    """The executable that starts the MCP server."""

    args: list[str] = Field(default_factory=list)
    """Arguments passed to the command."""

    env: dict[str, str] | None = None
    """Additional environment variables for the server process."""
