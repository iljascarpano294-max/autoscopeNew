# -*- coding: utf-8 -*-
"""Adapters to convert functions to the tool protocol."""
import inspect
import json
from typing import Callable, Any, AsyncGenerator, Generator

from pydantic import BaseModel

from ._types import Function
from ._base import ToolBase, ToolMiddlewareBase
from ._response import ToolChunk
from ._utils import (
    _extract_func_description,
    _extract_input_schema,
    _remove_title_field,
)
from ..message import (
    TextBlock,
    ToolResultState,
)


class FunctionTool(ToolBase):
    """Adapter to convert a Python function to ToolProtocol.

    This class wraps a regular Python function and makes it compatible with
    the ToolProtocol interface. It automatically extracts metadata from the
    function's signature and docstring, and normalizes the return value to
    ToolChunk or AsyncGenerator[ToolChunk, None].
    """

    is_external_tool: bool = False
    """If this tool is an external tool, which doesn't need to implement the
    __call__ method and the agent will yield the external tool call event."""
    is_mcp: bool = False
    """If this tool is an MCP tool, which will be used in the permission"""
    mcp_name: str | None = None
    """The name of the MCP server this tool belongs to, which is required if
    this tool is an MCP tool."""

    def __init__(
        self,
        func: Function,
        name: str | None = None,
        description: str | None = None,
        input_schema: dict | type[BaseModel] | None = None,
        is_concurrency_safe: bool = True,
        is_read_only: bool = False,
        is_state_injected: bool = False,
        middlewares: list[ToolMiddlewareBase] | None = None,
    ) -> None:
        """Initialize the FunctionTool.

        Args:
            func (`Callable`):
                The Python function to wrap.
            name (`str | None`, optional):
                Custom tool name. If None, uses the function name.
            description (`str | None`, optional):
                Custom tool description. If None, extracts from docstring.
            input_schema (`dict | type[BaseModel] | None`, optional):
                Custom input schema for the tool, either a JSON schema
                dict or a pydantic ``BaseModel`` subclass (converted via
                its ``model_json_schema()``). If None, generates the
                schema from the function's type annotations and
                docstring, where constraints (e.g. enums, value ranges)
                can be expressed with ``typing.Literal`` and
                ``typing.Annotated`` with ``pydantic.Field``.
            is_concurrency_safe (`bool`, optional):
                Whether this tool is safe to call concurrently.
            is_read_only (`bool`, optional):
                Whether this tool only reads data without side effects.
            is_state_injected (`bool`, optional):
                Whether this tool requires agent state injection.
            middlewares (`list[ToolMiddlewareBase] | None`, optional):
                Tool middlewares wrapping the tool execution.
        """
        super().__init__(middlewares=middlewares)
        self.name = name or func.__name__
        self.description = description or _extract_func_description(
            func.__doc__ or "",
        )
        if isinstance(input_schema, type) and issubclass(
            input_schema,
            BaseModel,
        ):
            input_schema = _remove_title_field(
                input_schema.model_json_schema(),
            )
        self.input_schema = input_schema or _extract_input_schema(func)
        self.is_concurrency_safe = is_concurrency_safe
        self.is_read_only = is_read_only
        self.is_state_injected = is_state_injected
        self.is_external_tool = False
        self.is_mcp = False
        self._func = func

    async def call(
        self,
        **kwargs: Any,
    ) -> ToolChunk | AsyncGenerator[ToolChunk, None]:
        """Invoke the wrapped function in an async style.

        Returns:
            `ToolChunk` or `AsyncGenerator[ToolChunk, None]`:
                The normalized result of the function execution.
        """
        if inspect.iscoroutinefunction(self._func):
            result = await self._func(**kwargs)
        else:
            result = self._func(**kwargs)

        if isinstance(result, AsyncGenerator):

            async def _stream() -> AsyncGenerator[ToolChunk, None]:
                async for chunk in result:
                    if isinstance(chunk, ToolChunk):
                        yield chunk
                    else:
                        yield self._convert_func_result_to_chunk(chunk)

            return _stream()

        if isinstance(result, Generator):

            async def _stream() -> AsyncGenerator[ToolChunk, None]:
                for chunk in result:
                    if isinstance(chunk, ToolChunk):
                        yield chunk
                    else:
                        yield self._convert_func_result_to_chunk(chunk)

            return _stream()

        return self._convert_func_result_to_chunk(result)

    @staticmethod
    def _convert_func_result_to_chunk(
        result: Any,
    ) -> ToolChunk:
        if isinstance(result, ToolChunk):
            return result
        if isinstance(result, str):
            text = result
        else:
            try:
                text = json.dumps(result, ensure_ascii=False)
            except (TypeError, ValueError):
                text = str(result)
        return ToolChunk(
            content=[TextBlock(text=text)],
            state=ToolResultState.RUNNING,
        )


# MCPTool arrives with stage 8 (workspace, MCP and skills).
__all__ = ["FunctionTool"]
