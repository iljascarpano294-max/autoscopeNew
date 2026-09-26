"""Stage 8 task 2: builtin file and command tools on the local workspace."""

import asyncio
import json
import sys

import pytest

from agentscope.message import TextBlock, ToolCallBlock, ToolResultState
from agentscope.state import AgentState
from agentscope.tool import (
    Bash,
    Edit,
    Glob,
    Grep,
    Read,
    ToolResponse,
    Write,
)
from agentscope.tool import Toolkit
from agentscope.workspace import LocalWorkspace, WorkspaceError


@pytest.fixture()
def workspace(tmp_path):
    ws = LocalWorkspace(root=tmp_path / "ws")
    asyncio.run(ws.write("notes/hello.txt", "hello workspace\nsecond line\n"))
    asyncio.run(ws.write("notes/code.py", "def add(a, b):\n    return a + b\n"))
    return ws


def _run_tool(tool, **tool_input):
    """Dispatch through Toolkit.call_tool, the real execution path."""
    toolkit = Toolkit(tools=[tool])
    call = ToolCallBlock(id="call-1", name=tool.name, input=json.dumps(tool_input))

    async def run():
        chunks, response = [], None
        async for item in toolkit.call_tool(call, AgentState()):
            if isinstance(item, ToolResponse):
                response = item
            else:
                chunks.append(item)
        return chunks, response

    return asyncio.run(run())


def _text(response) -> str:
    return "".join(
        block.text for block in response.content if isinstance(block, TextBlock)
    )


def test_file_round_trip(workspace) -> None:
    write, read = Write(workspace=workspace), Read(workspace=workspace)

    _, response = _run_tool(write, file_path="docs/new.txt", content="written by tool")
    assert response.state == ToolResultState.SUCCESS
    assert workspace.root.joinpath("docs/new.txt").read_text(encoding="utf-8") == (
        "written by tool"
    )

    _, response = _run_tool(read, file_path="docs/new.txt")
    assert response.state == ToolResultState.SUCCESS
    assert "written by tool" in _text(response)

    edit = Edit(workspace=workspace)
    _, response = _run_tool(
        edit,
        file_path="docs/new.txt",
        old_string="written",
        new_string="replaced",
    )
    assert response.state == ToolResultState.SUCCESS
    assert "replaced by tool" in workspace.root.joinpath("docs/new.txt").read_text(
        encoding="utf-8",
    )

    # Edit fails structurally when the old text is not found.
    _, response = _run_tool(
        edit,
        file_path="docs/new.txt",
        old_string="absent text",
        new_string="x",
    )
    assert response.state == ToolResultState.ERROR

    glob = Glob(workspace=workspace)
    _, response = _run_tool(glob, pattern="**/*.txt")
    assert response.state == ToolResultState.SUCCESS
    matched = _text(response)
    assert "docs/new.txt" in matched
    assert "notes/hello.txt" in matched

    grep = Grep(workspace=workspace)
    _, response = _run_tool(grep, pattern="hello")
    assert response.state == ToolResultState.SUCCESS
    assert "notes/hello.txt" in _text(response)


def test_tools_respect_workspace_boundary(workspace) -> None:
    read = Read(workspace=workspace)
    _, response = _run_tool(read, file_path="../outside.txt")
    assert response.state == ToolResultState.ERROR
    assert "workspace root" in _text(response)


def test_bash_runs_command_with_timeout(workspace) -> None:
    bash = Bash(workspace=workspace)
    _, response = _run_tool(bash, command="echo hello-bash")
    assert response.state == ToolResultState.SUCCESS
    assert "hello-bash" in _text(response)


def test_bash_timeout_does_not_hang(workspace) -> None:
    bash = Bash(workspace=workspace, timeout=1)
    _, response = _run_tool(
        bash,
        command=(
            f"{sys.executable} -c \"import time; print('started', flush=True);"
            " time.sleep(30)\""
        ),
    )
    # The command is killed at the timeout and reported as a failure.
    assert response.state == ToolResultState.ERROR
    assert "timed out" in _text(response).lower()


def test_bash_output_limit(workspace) -> None:
    bash = Bash(workspace=workspace, max_output_length=200)
    _, response = _run_tool(bash, command=f"{sys.executable} -c \"print('x' * 5000)\"")
    assert response.state == ToolResultState.SUCCESS
    assert len(_text(response)) <= 400
