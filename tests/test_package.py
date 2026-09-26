"""Smoke checks for the stage 0 package skeleton."""

from pathlib import Path

import agentscope


def test_import_uses_this_checkout() -> None:
    expected = Path(__file__).resolve().parents[1] / "src" / "agentscope" / "__init__.py"
    assert Path(agentscope.__file__).resolve() == expected.resolve()


def test_skeleton_version() -> None:
    assert agentscope.__version__ == "0.0.0"
