# -*- coding: utf-8 -*-
"""The Docker sandbox backend: one container per workspace instance."""
import asyncio
import subprocess

from .._sandboxed_base import ExecResult, SandboxBackendBase
from ._limits import DockerLimits


class DockerBackend(SandboxBackendBase):
    """Run the sandbox in a Docker container.

    The container is created with the configured memory/CPU limits and,
    by default, no network. Commands run through ``docker exec`` with a
    hard timeout (the exec process is killed on expiry); file writes go
    through ``docker exec cat >`` so nothing is mounted from the host.
    """

    def __init__(self, limits: DockerLimits | None = None) -> None:
        self.limits = limits or DockerLimits()
        self.container_id: str | None = None

    async def create(self) -> None:
        args = ["docker", "run", "-d", "--rm"]
        if self.limits.memory:
            args += ["--memory", self.limits.memory]
        if self.limits.cpus:
            args += ["--cpus", self.limits.cpus]
        if not self.limits.network:
            args += ["--network", "none"]
        args += ["-w", "/workspace", self.limits.image, "sleep", "infinity"]

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"Docker container creation failed: {stderr.decode(errors='replace')}",
            )
        self.container_id = stdout.decode().strip()[:12]

    async def execute(self, command: str, timeout: float = 60) -> ExecResult:
        if self.container_id is None:
            raise RuntimeError("The Docker container is not created.")
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", self.container_id, "bash", "-c", command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=f"command killed after {timeout}s timeout",
                timed_out=True,
            )
        return ExecResult(
            exit_code=process.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )

    async def write_file(self, path: str, content: str) -> None:
        if self.container_id is None:
            raise RuntimeError("The Docker container is not created.")
        target = f"/workspace/{path}"
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", "-i", self.container_id,
            "sh", "-c", f"mkdir -p \"$(dirname '{target}')\" && cat > '{target}'",
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = await process.communicate(content.encode())
        if process.returncode != 0:
            raise RuntimeError(
                f"Docker file write failed: {stderr.decode(errors='replace')}",
            )

    async def read_file(self, path: str) -> str:
        if self.container_id is None:
            raise RuntimeError("The Docker container is not created.")
        from .._base import WorkspaceError

        process = await asyncio.create_subprocess_exec(
            "docker", "exec", self.container_id, "cat", f"/workspace/{path}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise WorkspaceError(
                f"File '{path}' cannot be read from the sandbox: "
                f"{stderr.decode(errors='replace')}",
            )
        return stdout.decode()

    async def close(self) -> None:
        if self.container_id is None:
            return
        container_id, self.container_id = self.container_id, None
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", container_id,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await process.wait()
        except (OSError, subprocess.SubprocessError):
            pass  # best-effort cleanup
