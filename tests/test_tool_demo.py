"""Stage 4 tool demo: one offline reasoning-acting round."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "tool_demo.py"


def test_tool_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "5" in result.stdout
    assert "tool_call" in result.stdout
    assert "tool_result" in result.stdout
