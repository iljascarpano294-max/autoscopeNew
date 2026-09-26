# -*- coding: utf-8 -*-
"""The workspace module of agentscope."""

from ._base import LocalWorkspace, WorkspaceBase, WorkspaceError
from ._sandboxed_base import ExecResult, SandboxBackendBase, SandboxedWorkspace

__all__ = [
    "ExecResult",
    "LocalWorkspace",
    "SandboxBackendBase",
    "SandboxedWorkspace",
    "WorkspaceBase",
    "WorkspaceError",
]
