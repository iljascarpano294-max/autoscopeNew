# -*- coding: utf-8 -*-
"""Adapter to convert an MCP tool to the agentscope tool protocol.

Migrated from the reference implementation (commit 5ff52f8,
tool/_adapters.py), with the session management delegated to the local
:class:`~agentscope.mcp.MCPClient`.
"""
import re
from typing import Any

import mcp

from ..tool._base import ToolBase
from ..tool._response import ToolChunk
from ..message import (
    TextBlock,
    DataBlock,
    Base64Source,
    ToolResultState,
)


class MCPTool(ToolBase):
    """Adapter that exposes one MCP server tool to the agent."""

    is_mcp: bool = True
    """Whether this tool is an MCP tool."""
    is_state_injected: bool = False
    """The mcp tools is prohibited state injection for safety reason."""

    def __init__(
        self,
        mcp_name: str,
        tool: mcp.types.Tool,
        client: Any | None = None,
    ) -> None:
        """Initialize the MCPTool.

        Args:
            mcp_name (`str`):
                The name of the MCP server instance.
            tool (`mcp.types.Tool`):
                The MCP tool definition.
            client (`MCPClient | None`):
                The client used to reach the server; ``None`` only for
                schema-only inspection.
        """
        super().__init__()
        self.mcp_name = mcp_name

        # LLM providers enforce ^[a-zA-Z0-9_-]+$ on tool names.
        # tool.name comes from the MCP server and may contain dots,
        # colons, etc. — replace illegal chars with "x" (not "_") to
        # avoid collisions with the "__" separator.
        # self._tool.name retains the original for server-side calls.
        sanitized_tool = re.sub(r"[^a-zA-Z0-9_-]", "x", tool.name)
        self.name = f"mcp__{mcp_name}__{sanitized_tool}"
        if sanitized_tool != tool.name:
            from .._logging import logger

            logger.debug(
                "MCP tool name sanitized: '%s' -> '%s'.",
                tool.name,
                self.name,
            )

        self.description = tool.description or ""

        # Preserve the full inputSchema (including $defs, anyOf, oneOf, etc.)
        # rather than only copying "properties" and "required", which would
        # silently drop any nested type definitions that the LLM needs to
        # resolve $ref pointers.
        _schema = dict(tool.inputSchema) if tool.inputSchema else {}
        _schema.setdefault("type", "object")
        _schema.setdefault("properties", {})
        _schema.setdefault("required", [])
        self.input_schema = _schema

        # By default
        self.is_concurrency_safe = False
        self.is_external_tool = False

        # Extract is_read_only from MCP tool annotations
        self.is_read_only = False
        if tool.annotations and hasattr(tool.annotations, "readOnlyHint"):
            self.is_read_only = tool.annotations.readOnlyHint or False

        self._tool = tool
        self._client = client

    async def check_permissions(self, tool_input, context):
        """Read-only MCP tools are allowed; the rest ask the user."""
        from ..permission import PermissionBehavior, PermissionDecision

        if self.is_read_only:
            return PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="This is a read-only MCP tool. Allowing execution.",
            )
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="MCP tools must be explicitly allowed by the user.",
        )

    async def call(self, **kwargs: Any) -> ToolChunk:
        """Invoke the MCP tool and convert the result to a ToolChunk."""
        result = await self._client.call_tool(self._tool.name, kwargs)

        return ToolChunk(
            content=self._convert_mcp_content_to_blocks(result.content),
            state=ToolResultState.ERROR if result.isError else ToolResultState.RUNNING,
        )

    @staticmethod
    def _convert_mcp_content_to_blocks(mcp_content_blocks: list) -> list:
        """Convert MCP content blocks to agentscope blocks."""
        as_content = []
        for content in mcp_content_blocks:
            if isinstance(content, mcp.types.TextContent):
                as_content.append(TextBlock(text=content.text))
            elif isinstance(
                content,
                (mcp.types.ImageContent, mcp.types.AudioContent),
            ):
                as_content.append(
                    DataBlock(
                        source=Base64Source(
                            type="base64",
                            media_type=content.mimeType,
                            data=content.data,
                        ),
                    ),
                )
            else:
                from .._logging import logger

                logger.warning(
                    "Unsupported MCP content type: %s. Skipping it.",
                    type(content),
                )
        return as_content
