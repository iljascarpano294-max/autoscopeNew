# -*- coding: utf-8 -*-
"""The MCP client: manage one local stdio MCP server session."""
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ._config import StdioMCPConfig


class MCPClient:
    """Connect to one MCP server over stdio and expose its tools.

    The session lifecycle is explicit: ``connect`` opens the subprocess
    and performs the MCP handshake, ``close`` releases it. Tools are
    discovered with ``list_tools``; every call goes through
    ``call_tool`` so a closed connection surfaces as a structured error
    instead of a hang or a silent retry.
    """

    def __init__(self, name: str, config: StdioMCPConfig) -> None:
        self.name = name
        self.config = config
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        """Start the server subprocess and initialize the MCP session."""
        if self._session is not None:
            return
        params = StdioServerParameters(
            command=self.config.command,
            args=list(self.config.args),
            env=self.config.env,
        )
        self._stack = AsyncExitStack()
        try:
            read_stream, write_stream = await self._stack.enter_async_context(
                stdio_client(params),
            )
            self._session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream),
            )
            await self._session.initialize()
        except BaseException:
            await self._stack.aclose()
            self._stack = None
            self._session = None
            raise

    async def list_tools(self) -> list:
        """Return the tools exposed by the server, wrapped as MCPTool."""
        if self._session is None:
            raise RuntimeError(
                f"MCP client '{self.name}' is not connected; call "
                f"connect() first.",
            )
        from ._mcp_tool import MCPTool

        result = await self._session.list_tools()
        return [
            MCPTool(mcp_name=self.name, tool=tool, client=self)
            for tool in result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke one tool on the server and return its CallToolResult."""
        if self._session is None:
            raise RuntimeError(
                f"MCP client '{self.name}' is not connected; call "
                f"connect() first.",
            )
        return await self._session.call_tool(tool_name, arguments=arguments)

    async def close(self) -> None:
        """Shut the server session and subprocess down."""
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None
