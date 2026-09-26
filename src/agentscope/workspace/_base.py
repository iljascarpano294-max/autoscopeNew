# -*- coding: utf-8 -*-
"""The workspace abstraction for controlled file and command tools.

Stage 8 keeps the plan-specified minimal slice: a root directory, a path
resolver that enforces the root boundary (defeating ``..`` escapes,
outside absolute paths and escaping symlinks), and read/write helpers.
The reference project's workspace system (backends, sandboxes, skill
partitions, MCP gateways) is layered on the same ideas and arrives with
the remote-sandbox stage.
"""
from abc import ABC, abstractmethod
from pathlib import Path

from ..exception import AgentOrientedException


class WorkspaceError(AgentOrientedException):
    """Unified failure for workspace path and file operations.

    Raised for path escapes, missing files and decoding errors so the
    agent receives one structured, explainable error type.
    """


class WorkspaceBase(ABC):
    """Base class for workspaces: a controlled root directory."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        """The workspace root directory."""
        return self._root

    @abstractmethod
    def resolve_path(self, path: str) -> Path:
        """Resolve ``path`` against the root, enforcing the boundary.

        Returns:
            `Path`:
                An absolute path that is guaranteed to stay inside the
                root, symlinks followed.
        Raises:
            `WorkspaceError`:
                If the path escapes the root.
        """

    async def read(self, path: str) -> str:
        """Read a text file inside the root."""
        file_path = self.resolve_path(path)
        if not file_path.is_file():
            raise WorkspaceError(
                f"File '{path}' does not exist in the workspace root "
                f"'{self._root}'.",
            )
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise WorkspaceError(
                f"File '{path}' is not valid UTF-8 text: {error}",
            ) from error

    async def write(self, path: str, content: str) -> Path:
        """Write a text file inside the root, creating parent directories."""
        file_path = self.resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path


class LocalWorkspace(WorkspaceBase):
    """A workspace bound to a local directory."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self._root.mkdir(parents=True, exist_ok=True)
        # Resolve the root itself so symlinked roots compare correctly.
        self._resolved_root = self._root.resolve()

    def resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self._root / candidate

        # resolve() follows symlinks in every existing component, so a
        # link pointing outside the root resolves to a path outside it.
        resolved = candidate.resolve()
        if resolved != self._resolved_root and not resolved.is_relative_to(
            self._resolved_root,
        ):
            raise WorkspaceError(
                f"Path '{path}' escapes the workspace root "
                f"'{self._resolved_root}'.",
            )
        return resolved
