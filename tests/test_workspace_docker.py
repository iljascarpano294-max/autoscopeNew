"""Stage 14 task 2: the Docker backend (integration; skipped offline)."""

import shutil
import subprocess

import pytest

from agentscope.workspace import DockerBackend, DockerLimits, SandboxedWorkspace


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


docker_ready = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available; integration test skipped offline",
)


@pytest.mark.integration
@docker_ready
def test_docker_parity() -> None:
    async def run():
        backend = DockerBackend(
            DockerLimits(image="python:3.11-slim", memory="256m", cpus="0.5", network=False),
        )
        workspace = SandboxedWorkspace(backend=backend)
        await workspace.create()
        try:
            await workspace.write("notes/hello.txt", "hello docker")
            content = await workspace.read("notes/hello.txt")
            result = await workspace.execute("cat /workspace/notes/hello.txt && echo done", timeout=20)
            timed = await workspace.execute("sleep 30", timeout=2)
            return content, result, timed
        finally:
            await workspace.close()
            await workspace.close()  # double close is safe

    content, result, timed = asyncio_run(run())

    assert content == "hello docker"
    assert "hello docker" in result.stdout
    assert result.exit_code == 0
    assert timed.timed_out is True


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
