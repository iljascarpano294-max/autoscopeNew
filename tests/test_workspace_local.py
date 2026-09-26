"""Stage 8 task 1: local workspace path boundary."""

import asyncio
import os

import pytest

from agentscope.workspace import LocalWorkspace, WorkspaceError


def test_workspace_boundary(tmp_path) -> None:
    workspace = LocalWorkspace(root=tmp_path / "ws")

    # A plain relative path round-trips through the boundary.
    asyncio.run(workspace.write("notes/hello.txt", "hello workspace"))
    assert asyncio.run(workspace.read("notes/hello.txt")) == "hello workspace"

    # ../ escapes are rejected.
    with pytest.raises(WorkspaceError):
        workspace.resolve_path("../escape.txt")
    with pytest.raises(WorkspaceError):
        workspace.resolve_path("notes/../../escape.txt")

    # Absolute paths outside the root are rejected.
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(WorkspaceError):
        workspace.resolve_path(str(outside))

    # A symlink pointing outside the root is rejected on read.
    link = workspace.root / "sneaky.txt"
    if hasattr(os, "symlink"):
        try:
            os.symlink(outside, link)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")
        with pytest.raises(WorkspaceError):
            asyncio.run(workspace.read("sneaky.txt"))
        with pytest.raises(WorkspaceError):
            workspace.resolve_path("sneaky.txt")

        # A symlink that stays inside the root is fine.
        target = workspace.root / "notes" / "hello.txt"
        inside_link = workspace.root / "inside_link.txt"
        os.symlink(target, inside_link)
        assert asyncio.run(workspace.read("inside_link.txt")) == "hello workspace"


def test_nonexistent_and_encoding_errors_are_structured(tmp_path) -> None:
    workspace = LocalWorkspace(root=tmp_path)

    # A missing file yields a structured failure, not FileNotFoundError.
    with pytest.raises(WorkspaceError, match="missing.txt"):
        asyncio.run(workspace.read("missing.txt"))

    # Invalid UTF-8 bytes yield a structured failure, not UnicodeDecodeError.
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(WorkspaceError, match="binary.bin"):
        asyncio.run(workspace.read("binary.bin"))


def test_resolve_path_returns_absolute_path_inside_root(tmp_path) -> None:
    workspace = LocalWorkspace(root=tmp_path)
    resolved = workspace.resolve_path("a/b.txt")
    assert resolved.is_absolute()
    assert resolved == tmp_path / "a" / "b.txt"
