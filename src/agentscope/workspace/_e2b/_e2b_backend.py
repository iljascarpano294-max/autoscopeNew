# -*- coding: utf-8 -*-
"""The E2B cloud sandbox backend."""
from typing import Any, Callable

from .._base import WorkspaceError
from .._sandboxed_base import ExecResult, SandboxBackendBase


class E2BBackend(SandboxBackendBase):
    """Run the sandbox in E2B's cloud.

    The E2B SDK and API key (environment) are only required when no
    ``sandbox_factory`` is injected — tests and offline consumers inject
    a fake factory and never touch the network. Connection problems
    surface as structured errors naming the missing configuration.
    """

    def __init__(self, sandbox_factory: Callable[[], Any] | None = None) -> None:
        self._sandbox_factory = sandbox_factory
        self._sandbox: Any | None = None
        self._closed = False

    async def create(self) -> None:
        if self._sandbox_factory is not None:
            self._sandbox = await self._sandbox_factory()
            self._closed = False
            return
        try:
            from e2b import AsyncSandbox  # noqa: F401
        except ImportError as error:
            raise RuntimeError(
                "The e2b backend needs the 'e2b' package installed and an "
                "E2B_API_KEY in the environment; install it or inject a "
                "sandbox_factory for offline use.",
            ) from error
        import os

        if not os.environ.get("E2B_API_KEY"):
            raise RuntimeError(
                "The e2b backend needs the E2B_API_KEY environment "
                "variable; credentials never belong in code.",
            )
        self._sandbox = await AsyncSandbox.create()
        self._closed = False

    async def execute(self, command: str, timeout: float = 60) -> ExecResult:
        sandbox = self._require_sandbox()
        try:
            result = await sandbox.commands.run(command, timeout=timeout)
        except TimeoutError:
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=f"command killed after {timeout}s timeout",
                timed_out=True,
            )
        return ExecResult(
            exit_code=result.exit_code,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    async def write_file(self, path: str, content: str) -> None:
        sandbox = self._require_sandbox()
        await sandbox.files.write(f"/workspace/{path}", content)

    async def read_file(self, path: str) -> str:
        sandbox = self._require_sandbox()
        try:
            return await sandbox.files.read(f"/workspace/{path}")
        except FileNotFoundError as error:
            raise WorkspaceError(
                f"File '{path}' does not exist in the sandbox.",
            ) from error

    async def close(self) -> None:
        if self._sandbox is not None and not self._closed:
            self._closed = True
            await self._sandbox.close()
        self._sandbox = None

    def _require_sandbox(self) -> Any:
        if self._sandbox is None:
            raise RuntimeError("The e2b sandbox is not created.")
        return self._sandbox
