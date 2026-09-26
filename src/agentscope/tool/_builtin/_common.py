# -*- coding: utf-8 -*-
"""Shared base for the built-in workspace tools."""
from typing import Any, List

from .._base import ToolBase, ToolMiddlewareBase
from .._response import ToolChunk
from ...message import TextBlock, ToolResultState
from ...permission import PermissionBehavior, PermissionDecision
from ...workspace import LocalWorkspace, WorkspaceError


class WorkspaceTool(ToolBase):
    """A tool bound to a :class:`LocalWorkspace`.

    Every path argument flows through ``workspace.resolve_path`` so the
    workspace root boundary (``..`` escapes, outside absolute paths,
    escaping symlinks) applies to all built-in tools. Workspace failures
    surface as ERROR tool chunks the agent can observe and react to.
    """

    def __init__(
        self,
        workspace: LocalWorkspace,
        middlewares: List[ToolMiddlewareBase] | None = None,
    ) -> None:
        super().__init__(middlewares=middlewares)
        self.workspace = workspace

    async def check_permissions(self, tool_input, context) -> PermissionDecision:
        """Defer to the permission engine: read-only invocations are
        auto-allowed by the engine's fast path, the rest follow the
        configured rules and mode."""
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Workspace tools defer to the permission engine",
        )

    @staticmethod
    def _ok(text: str) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text=text)])

    @staticmethod
    def _error(text: str) -> ToolChunk:
        return ToolChunk(
            content=[TextBlock(type="text", text=text)],
            state=ToolResultState.ERROR,
        )

    async def _guarded(self, path: str, action) -> ToolChunk:
        """Await a file operation coroutine, mapping workspace failures to
        error chunks."""
        try:
            return await action
        except WorkspaceError as error:
            return self._error(str(error))
