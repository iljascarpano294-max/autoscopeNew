"""Stage 14 task 1: the sandboxed workspace contract over a Fake backend."""

import asyncio

import pytest

from agentscope.workspace import (
    ExecResult,
    LocalWorkspace,
    SandboxBackendBase,
    SandboxedWorkspace,
    WorkspaceError,
)


class FakeBackend(SandboxBackendBase):
    """Records the call order; emulates file and command execution."""

    def __init__(self, fail_create: bool = False) -> None:
        self.calls: list = []
        self.files: dict = {}
        self.fail_create = fail_create
        self.closed = False

    async def create(self) -> None:
        self.calls.append("create")
        if self.fail_create:
            raise RuntimeError("image pull failed")
        self.files["/workspace/.keep"] = ""

    async def execute(self, command: str, timeout: float = 60) -> ExecResult:
        self.calls.append(f"execute:{command}")
        if "sleep" in command and "30" in command:
            return ExecResult(exit_code=-1, stdout="", stderr="terminated: timeout", timed_out=True)
        return ExecResult(exit_code=0, stdout=f"ran: {command}", stderr="")

    async def write_file(self, path: str, content: str) -> None:
        self.calls.append(f"write:{path}")
        self.files[path] = content

    async def read_file(self, path: str) -> str:
        self.calls.append(f"read:{path}")
        if path not in self.files:
            raise WorkspaceError(f"File '{path}' does not exist in the sandbox.")
        return self.files[path]

    async def close(self) -> None:
        self.calls.append("close")
        self.closed = True


def test_fake_backend_lifecycle() -> None:
    backend = FakeBackend()
    workspace = SandboxedWorkspace(backend=backend)

    async def run():
        await workspace.create()
        await workspace.write("notes/plan.txt", "the plan")
        content = await workspace.read("notes/plan.txt")
        result = await workspace.execute("ls -la", timeout=10)
        return content, result

    content, result = asyncio.run(run())

    assert content == "the plan"
    assert result.exit_code == 0
    assert result.stdout == "ran: ls -la"
    # The lifecycle order is create -> file ops -> execute -> (close later).
    assert backend.calls[0] == "create"
    assert backend.calls[-1].startswith("execute")

    # Closing twice is safe.
    await_none = asyncio.run(workspace.close())
    assert await_none is None
    asyncio.run(workspace.close())
    assert backend.closed


def test_execute_timeout_is_reported() -> None:
    backend = FakeBackend()
    workspace = SandboxedWorkspace(backend=backend)
    asyncio.run(workspace.create())

    result = asyncio.run(workspace.execute("sleep 30", timeout=1))
    assert result.timed_out is True
    assert result.exit_code != 0


def test_sandbox_path_boundary_still_applies() -> None:
    workspace = SandboxedWorkspace(backend=FakeBackend())
    with pytest.raises(WorkspaceError):
        workspace.resolve_path("../escape.txt")


def test_create_failure_cleans_up() -> None:
    backend = FakeBackend(fail_create=True)
    workspace = SandboxedWorkspace(backend=backend)

    with pytest.raises(RuntimeError, match="image pull failed"):
        asyncio.run(workspace.create())

    # The failed create still attempted to release the resources.
    assert "close" in backend.calls
    assert workspace.is_created is False
    # File operations on an uncreated sandbox are refused.
    with pytest.raises(WorkspaceError, match="not created"):
        asyncio.run(workspace.read("notes/plan.txt"))


def test_local_workspace_still_works_alongside() -> None:
    # The stage 8 local workspace remains untouched by the sandbox layer.
    import tempfile
    from pathlib import Path

    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            local = LocalWorkspace(root=Path(tmp) / "ws")
            await local.write("a.txt", "local")
            return await local.read("a.txt")

    assert asyncio.run(run()) == "local"
