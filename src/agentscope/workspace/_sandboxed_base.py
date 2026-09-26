# -*- coding: utf-8 -*-
"""The sandboxed workspace: the stage-8 file/command semantics over a
replaceable remote backend (Docker, E2B, Daytona, K8s, ...)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ._base import LocalWorkspace, WorkspaceBase, WorkspaceError


@dataclass
class ExecResult:
    """One command execution in the sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    """True when the command was killed after the timeout."""


class SandboxBackendBase(ABC):
    """The lifecycle and I/O of one remote sandbox instance."""

    @abstractmethod
    async def create(self) -> None:
        """Create/start the sandbox; raises on failure so the workspace
        can attempt cleanup."""

    @abstractmethod
    async def execute(self, command: str, timeout: float = 60) -> ExecResult:
        """Run a command inside the sandbox; the backend must terminate
        the process when the timeout expires."""

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """Write a text file into the sandbox (path relative to root)."""

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read a text file from the sandbox."""

    @abstractmethod
    async def close(self) -> None:
        """Tear the sandbox down; must be safe to call twice."""


class SandboxedWorkspace(WorkspaceBase):
    """A workspace whose files and commands live in a remote sandbox.

    The stage-8 path boundary is enforced lexically here (remote
    sandboxes have no local symlinks to resolve); the backend owns the
    actual isolation. Creation is explicit: file/command operations on
    an uncreated (or failed) sandbox are refused, and a failed create
    still attempts to release whatever the backend provisioned.
    """

    def __init__(self, backend: SandboxBackendBase) -> None:
        # The in-sandbox root is virtual; the local Path root is unused.
        super().__init__(root=Path("/workspace"))
        self.backend = backend
        self.is_created = False

    async def create(self) -> None:
        try:
            await self.backend.create()
            self.is_created = True
        except Exception:
            await self._cleanup_quietly()
            raise

    async def _cleanup_quietly(self) -> None:
        try:
            await self.backend.close()
        except Exception:
            pass  # best-effort cleanup on an already-failing create

    def _require_created(self) -> None:
        if not self.is_created:
            raise WorkspaceError(
                "The sandbox is not created; call create() first.",
            )

    def resolve_path(self, path: str) -> Path:
        # Lexical boundary: real symlink resolution happens inside the
        # sandbox filesystem, which the backend isolates per instance.
        if not self.is_created:
            raise WorkspaceError(
                "The sandbox is not created; call create() first.",
            )
        candidate = Path(path)
        if candidate.is_absolute():
            # Absolute paths are interpreted inside the sandbox root.
            candidate = Path(*candidate.parts[1:]) if len(candidate.parts) > 1 else Path()
        resolved = Path("/workspace") / candidate
        try:
            resolved.relative_to(Path("/workspace"))
        except ValueError as error:
            raise WorkspaceError(
                f"Path '{path}' escapes the sandbox root '/workspace'.",
            ) from error
        return resolved

    async def read(self, path: str) -> str:
        self._require_created()
        self.resolve_path(path)
        return await self.backend.read_file(path)

    async def write(self, path: str, content: str) -> Path:
        self._require_created()
        self.resolve_path(path)
        await self.backend.write_file(path, content)
        return Path("/workspace") / path

    async def execute(self, command: str, timeout: float = 60) -> ExecResult:
        self._require_created()
        return await self.backend.execute(command, timeout=timeout)

    async def close(self) -> None:
        """Tear the sandbox down; safe to call multiple times."""
        if not self.is_created:
            return
        self.is_created = False
        await self.backend.close()
