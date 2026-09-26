"""Stage 14 demo: the same workspace use cases, local or in a sandbox.

Default mode is local (no services required). Pass --docker to run the
same file/command use cases inside a Docker container instead (requires
a Docker daemon); the sandbox backend owns creation, execution,
timeout and cleanup.

Deployment notes (Aliyun ECS planning, not exercised here): the Docker
backend needs the container runtime installed, images pre-pulled, and
memory/CPU limits sized per session; containers are removed with
``docker rm -f`` on close, and crashed sessions are covered by the same
best-effort cleanup path. Credentials stay in environment variables.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

from agentscope.workspace import LocalWorkspace, SandboxedWorkspace


async def run_use_cases(workspace) -> None:
    await workspace.write("notes/demo.txt", "sandbox demo")
    content = await workspace.read("notes/demo.txt")
    print(f"read back: {content!r}")


async def main() -> None:
    if "--docker" in sys.argv:
        from agentscope.workspace import DockerBackend, DockerLimits

        backend = DockerBackend(DockerLimits())
        workspace = SandboxedWorkspace(backend=backend)
        await workspace.create()
        try:
            await run_use_cases(workspace)
            result = await workspace.execute("cat /workspace/notes/demo.txt", timeout=20)
            print(f"executed: exit={result.exit_code} out={result.stdout.strip()!r}")
        finally:
            await workspace.close()
        return

    # Local mode: identical use cases against the stage 8 workspace.
    with tempfile.TemporaryDirectory() as tmp:
        workspace = LocalWorkspace(root=Path(tmp) / "ws")
        await run_use_cases(workspace)
    print("mode: local (use --docker for the container backend)")


if __name__ == "__main__":
    asyncio.run(main())
