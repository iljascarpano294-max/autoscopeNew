"""Stage 8 task 3: local stdio MCP server integration."""

import asyncio
import json
import sys

import pytest

from agentscope.message import TextBlock, ToolCallBlock, ToolResultState
from agentscope.mcp import MCPClient, StdioMCPConfig
from agentscope.state import AgentState
from agentscope.tool import Toolkit, ToolResponse

SERVER_SCRIPT = '''\
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return text


if __name__ == "__main__":
    mcp.run()
'''


@pytest.fixture()
def client(tmp_path):
    server = tmp_path / "echo_server.py"
    server.write_text(SERVER_SCRIPT, encoding="utf-8")
    return MCPClient(
        name="echo",
        config=StdioMCPConfig(command=sys.executable, args=[str(server)]),
    )


def test_local_mcp(client) -> None:
    async def run():
        toolkit = Toolkit()
        await toolkit.add_mcp(client)
        schemas = await toolkit.get_tool_schemas()

        call = ToolCallBlock(
            id="call-1",
            name="mcp__echo__echo",
            input=json.dumps({"text": "hi mcp"}),
        )
        chunks, response = [], None
        async for item in toolkit.call_tool(call, AgentState()):
            if isinstance(item, ToolResponse):
                response = item
            else:
                chunks.append(item)
        await client.close()
        return schemas, response

    schemas, response = asyncio.run(run())

    # The toolkit discovered the MCP tool and its schema.
    assert any(
        schema["function"]["name"] == "mcp__echo__echo" for schema in schemas
    )
    # Calling through the toolkit returned the echo result.
    assert response is not None
    assert response.state == ToolResultState.SUCCESS
    assert "hi mcp" in "".join(
        block.text for block in response.content if isinstance(block, TextBlock)
    )


def test_disconnected_mcp_returns_failure(client) -> None:
    async def run():
        toolkit = Toolkit()
        await toolkit.add_mcp(client)
        await client.close()

        call = ToolCallBlock(
            id="call-2",
            name="mcp__echo__echo",
            input=json.dumps({"text": "gone"}),
        )
        chunks, response = [], None
        async for item in toolkit.call_tool(call, AgentState()):
            if isinstance(item, ToolResponse):
                response = item
            else:
                chunks.append(item)
        return response

    response = asyncio.run(run())

    # A closed connection produces a structured failure, never a hang.
    assert response is not None
    assert response.state == ToolResultState.ERROR
