"""Stage 8 demo: workspace-bound file tools, command execution and skills.

All paths the tools see flow through LocalWorkspace.resolve_path, so
``..`` escapes, absolute paths outside the root and symlinks pointing
out of the root are rejected. The Bash tool runs with the workspace
root as its working directory, a hard timeout and an output cap.
"""

import asyncio
import tempfile
from pathlib import Path

from agentscope.message import TextBlock, ToolCallBlock
from agentscope.state import AgentState
from agentscope.tool import Bash, Glob, Read, Toolkit, ToolResponse, Write
from agentscope.workspace import LocalWorkspace


async def _run(toolkit: Toolkit, name: str, **tool_input: object) -> str:
    from json import dumps

    call = ToolCallBlock(id=f"demo-{name}", name=name, input=dumps(tool_input))
    chunks, response = [], None
    async for item in toolkit.call_tool(call, AgentState()):
        if isinstance(item, ToolResponse):
            response = item
        else:
            chunks.append(item)
    return "".join(
        block.text for block in response.content if isinstance(block, TextBlock)
    )


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        workspace = LocalWorkspace(root=Path(tmp) / "ws")
        toolkit = Toolkit(
            tools=[
                Write(workspace=workspace),
                Read(workspace=workspace),
                Glob(workspace=workspace),
                Bash(workspace=workspace, timeout=10),
            ],
        )

        print(await _run(toolkit, "Write", file_path="notes/demo.txt", content="demo"))
        print(await _run(toolkit, "Read", file_path="notes/demo.txt"))
        print(await _run(toolkit, "Glob", pattern="**/*.txt"))

        escape = await _run(toolkit, "Read", file_path="../secret.txt")
        print(f"escape attempt -> {escape.splitlines()[0]}")

        listing = await _run(toolkit, "Bash", command="dir /b 2>nul || ls")
        print(f"bash listing: {listing.strip().splitlines()[0]!r}")


if __name__ == "__main__":
    asyncio.run(main())
