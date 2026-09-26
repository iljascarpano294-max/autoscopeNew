# -*- coding: utf-8 -*-
"""The tool module in agentscope."""

from ._types import ToolChoice, Function, RegisteredTool
from ._response import ToolResponse, ToolChunk
from ._toolkit import Toolkit
from ._base import ToolBase, ParamsBase, ToolMiddlewareBase
from ._adapters import FunctionTool
from ._builtin import (
    Bash,
    Edit,
    Glob,
    Grep,
    Read,
    Write,
)
from ..mcp import MCPTool

__all__ = [
    # Basic tool related types and functions
    "ToolChoice",
    "Function",
    "ToolBase",
    "ParamsBase",
    "ToolMiddlewareBase",
    "FunctionTool",
    "Toolkit",
    "ToolChunk",
    "ToolResponse",
    "RegisteredTool",
    # Built-in workspace tools
    "Bash",
    "Edit",
    "Glob",
    "Grep",
    "Read",
    "Write",
    # MCP tools (hosted in agentscope.mcp, re-exported like the reference)
    "MCPTool",
]
