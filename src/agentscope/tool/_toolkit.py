# -*- coding: utf-8 -*-
"""The toolkit class for tool calls in AgentScope."""
import asyncio
import inspect
from collections import OrderedDict
from typing import AsyncGenerator, Generator

import jsonschema

from ._base import ToolBase
from ._response import ToolResponse, ToolChunk
from ._types import RegisteredTool
from .._logging import logger
from .._utils._common import _json_loads_with_repair
from ..exception import DeveloperOrientedException
from ..message import (
    ToolCallBlock,
    TextBlock,
    ToolResultState,
)
from ..state import AgentState


class Toolkit:
    """Toolkit is the core module to register, manage and execute tool
    functions in AgentScope.

    Stage 4 keeps the reference Toolkit's registration/dispatch surface for a
    single "basic" group: tool groups, MCP clients, agent skills and the
    built-in meta tools arrive with stages 8.

    About tool functions:

    - Register and parse JSON schemas from their docstrings automatically.
    - Tool function execution with unified streaming interface.
    """

    def __init__(
        self,
        tools: list[ToolBase] | None = None,
    ) -> None:
        """Initialize the toolkit.

        Args:
            tools (`list[ToolBase] | None`, optional):
                The tool objects that belong to the "basic" tool group.
        """
        self._registered_tools: OrderedDict[str, RegisteredTool] = (
            OrderedDict()
        )
        self._mcp_clients: list = []
        for tool in tools or []:
            self._register(tool)

    def _register(self, tool: ToolBase) -> None:
        """Register one tool, warning and overriding on duplicate names, the
        same behavior as the reference ``Toolkit.add_tool``."""
        if tool.name in self._registered_tools:
            logger.warning(
                "Duplicate tool name '%s' found in group 'basic', "
                "overwriting it.",
                tool.name,
            )
        self._registered_tools[tool.name] = RegisteredTool(tool=tool)

    async def get_tool_schemas(
        self,
        groups: list[str] | None = None,
    ) -> list[dict]:
        """Get the JSON schemas of the currently available tool functions.

        .. note:: Stage 4 only has the "basic" group, so ``groups`` is
        accepted for interface compatibility and has no filtering effect
        yet.

        Args:
            groups (`list[str] | None`, optional):
                A list of group names to filter the tool function.

        Returns:
            `list[dict]`:
                A list of function JSON schemas.
        """
        return [
            registered_tool.get_tool_schema()
            for registered_tool in self._registered_tools.values()
        ]

    async def call_tool(
        self,
        tool_call: ToolCallBlock,
        state: AgentState,
    ) -> AsyncGenerator[ToolChunk | ToolResponse, None]:
        """Call the tool function, return the incremental tool result in
        a ToolChunk stream, and finally return the complete tool result in a
        ToolResponse object. **Note the accumulation process occurs within this
        function, so the tool functions only need to return/yield the
        ToolChunk objects in an incremental manner.**

        Args:
            tool_call (`ToolCallBlock`):
                A tool call block.
            state (`AgentState`):
                The current agent state, used to state injection.

        Yields:
            `ToolChunk | ToolResponse`:
                The incremental tool result in a ToolChunk stream, and finally
                the complete tool result in a ToolResponse object.
        """
        tool_response = ToolResponse(id=tool_call.id)

        # Check
        registered_tool = self._registered_tools.get(tool_call.name)
        if registered_tool is None:
            # Not exist
            chunk = ToolChunk(
                content=[
                    TextBlock(
                        text=f"ToolNotFoundError: The tool named "
                        f"'{tool_call.name}' doesn't exist.",
                    ),
                ],
                state=ToolResultState.ERROR,
            )
            yield chunk
            yield tool_response.append_chunk(chunk)
            return

        # Obtain the tool function
        tool_func = registered_tool.tool

        # Async function
        try:
            # Prepare keyword arguments, repairing the argument types
            # against the tool schema when the model got them wrong.
            kwargs = _json_loads_with_repair(
                tool_call.input,
                tool_func.input_schema,
            )

            # json_repair only fixes malformed JSON and mismatched types;
            # validate the repaired arguments explicitly so that missing
            # required parameters never reach the tool implementation.
            jsonschema.validate(kwargs, tool_func.input_schema)

            # State injection
            if (
                tool_func.is_state_injected
                and not tool_func.is_mcp
                and not tool_func.is_external_tool
            ):
                kwargs["_agent_state"] = state

            if inspect.iscoroutinefunction(tool_func.__call__):
                res = await tool_func(**kwargs)
            else:
                # When `tool_func.__call__` is an async generator function or
                # sync function
                res = tool_func(**kwargs)

            if isinstance(res, ToolChunk):
                yield res
                tool_response.append_chunk(res)

            # If return an async generator
            elif isinstance(res, AsyncGenerator):
                async for chunk in res:
                    yield chunk
                    tool_response.append_chunk(chunk)

            # If return a sync generator
            elif isinstance(res, Generator):
                for chunk in res:
                    yield chunk
                    tool_response.append_chunk(chunk)

            else:
                raise DeveloperOrientedException(
                    "The tool function must return a ToolChunk object, or an "
                    "AsyncGenerator/Generator of ToolChunk objects, "
                    f"but got {type(res)}.",
                )

        except Exception as e:
            # Raise the developer-oriented exception
            if isinstance(e, DeveloperOrientedException):
                raise e from None

            # The exceptions should be handled by the agent
            chunk = ToolChunk(
                content=[
                    TextBlock(
                        type="text",
                        text=str(e),
                    ),
                ],
                state=ToolResultState.ERROR,
            )
            yield chunk
            tool_response.append_chunk(chunk)

        except asyncio.CancelledError:
            chunk = ToolChunk(
                content=[
                    TextBlock(
                        type="text",
                        text="<system-reminder>"
                        "The tool call has been interrupted "
                        "by the user."
                        "</system-reminder>",
                    ),
                ],
                state=ToolResultState.INTERRUPTED,
            )
            yield chunk
            tool_response.append_chunk(chunk)

        finally:
            # Finally, yield the complete tool response
            yield tool_response

    async def get_tool(self, name: str) -> ToolBase | None:
        """Get tool instance by its name.

        Args:
            name (`str`):
                The name of the tool to be checked.

        Returns:
            `ToolBase | None`:
                The tool instance, or `None` if no tool is found.
        """
        registered_tool = self._registered_tools.get(name, None)
        if registered_tool is None:
            return None
        return registered_tool.tool

    def clear(self) -> None:
        """Clear the registered tools."""
        self._registered_tools.clear()

    async def add_tool(
        self,
        tool: ToolBase | list[ToolBase],
    ) -> None:
        """Add tool to the toolkit on-the-fly.

        Args:
            tool (`ToolBase | list[ToolBase]`):
                The tool to be added.
        """
        new_tools = tool if isinstance(tool, list) else [tool]
        for new_tool in new_tools:
            self._register(new_tool)

    async def add_mcp(self, client) -> None:
        """Connect to an MCP client and register its tools.

        Args:
            client (`MCPClient`):
                The MCP client to connect to; it is stored so its tools
                stay reachable for the lifetime of the toolkit.
        """
        if not client.is_connected:
            await client.connect()
        self._mcp_clients.append(client)
        for mcp_tool in await client.list_tools():
            self._register(mcp_tool)

    async def remove_tool(self, tool_name: str | list[str]) -> None:
        """Remove tool from the toolkit on-the-fly.

        Args:
            tool_name (`str | list[str]`):
                The name of the tool to be removed.
        """
        if isinstance(tool_name, str):
            tool_name = [tool_name]

        for name in tool_name:
            self._registered_tools.pop(name, None)
