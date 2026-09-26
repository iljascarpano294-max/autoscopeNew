"""Stage 14 task 3: the E2B backend over a mock SDK."""

import asyncio

import pytest

from agentscope.workspace import (
    E2BBackend,
    ExecResult,
    SandboxedWorkspace,
    WorkspaceError,
)


class FakeCommandResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str = "") -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class _FakeCommands:
    def __init__(self, outer: "FakeSandbox") -> None:
        self._outer = outer

    async def run(self, command: str, timeout: float):
        self._outer.calls.append(f"execute:{command}")
        if "sleep" in command:
            raise TimeoutError("command timed out")
        return FakeCommandResult(exit_code=0, stdout=f"ran: {command}")


class _FakeFiles:
    def __init__(self, outer: "FakeSandbox") -> None:
        self._outer = outer

    async def write(self, path: str, content: str):
        self._outer.calls.append(f"write:{path}")
        self._outer.file_store[path] = content

    async def read(self, path: str):
        self._outer.calls.append(f"read:{path}")
        if path not in self._outer.file_store:
            raise FileNotFoundError(path)
        return self._outer.file_store[path]


class FakeSandbox:
    """Stands in for the e2b AsyncSandbox (commands/files namespaces)."""

    def __init__(self) -> None:
        self.calls: list = []
        self.file_store: dict = {}
        self.commands = _FakeCommands(self)
        self.files = _FakeFiles(self)

    async def close(self):
        self.calls.append("close")


def test_e2b_mock() -> None:
    sandbox = FakeSandbox()

    async def factory():
        sandbox.calls.append("create")
        return sandbox

    backend = E2BBackend(sandbox_factory=factory)
    workspace = SandboxedWorkspace(backend=backend)

    async def run():
        await workspace.create()
        await workspace.write("notes/plan.txt", "the plan")
        content = await workspace.read("notes/plan.txt")
        result = await workspace.execute("ls -la", timeout=10)
        await workspace.close()
        await workspace.close()  # double close is safe
        return content, result, sandbox.calls

    content, result, calls = asyncio.run(run())

    assert content == "the plan"
    assert isinstance(result, ExecResult)
    assert result.stdout == "ran: ls -la"
    assert calls[0] == "create"
    assert calls.count("close") == 1
    assert calls[-1] == "close"


def test_e2b_timeout_maps_to_timed_out_result() -> None:
    sandbox = FakeSandbox()

    async def factory():
        return sandbox

    backend = E2BBackend(sandbox_factory=factory)
    workspace = SandboxedWorkspace(backend=backend)

    async def run():
        await workspace.create()
        try:
            return await workspace.execute("sleep 30", timeout=1)
        finally:
            await workspace.close()

    result = asyncio.run(run())
    assert result.timed_out is True


def test_e2b_missing_file_is_structured() -> None:
    sandbox = FakeSandbox()

    async def factory():
        return sandbox

    workspace = SandboxedWorkspace(backend=E2BBackend(sandbox_factory=factory))

    async def run():
        await workspace.create()
        try:
            await workspace.read("missing.txt")
        finally:
            await workspace.close()

    with pytest.raises(WorkspaceError, match="missing.txt"):
        asyncio.run(run())
