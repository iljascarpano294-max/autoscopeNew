# -*- coding: utf-8 -*-
"""The workspace module of agentscope."""

from ._base import LocalWorkspace, WorkspaceBase, WorkspaceError
from ._docker import DockerBackend, DockerLimits
from ._e2b import E2BBackend
from ._sandboxed_base import ExecResult, SandboxBackendBase, SandboxedWorkspace

__all__ = [
    "DockerBackend",
    "DockerLimits",
    "E2BBackend",
    "ExecResult",
    "LocalWorkspace",
    "SandboxBackendBase",
    "SandboxedWorkspace",
    "WorkspaceBase",
    "WorkspaceError",
]
