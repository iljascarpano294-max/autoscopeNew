"""Stage 7 middleware demo smoke test."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "middleware_demo.py"


def test_middleware_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr

    # The recorded hook order shows the onion pattern: reply -> model call
    # -> acting -> second model call -> reply exit.
    lines = [
        line.strip().removeprefix("  ")
        for line in result.stdout.splitlines()
        if line.strip().startswith(("on_",))
    ]
    assert lines == [
        "on_reply:enter",
        "on_model_call:enter",
        "on_model_call:exit",
        "on_acting:enter(add)",
        "on_acting:exit",
        "on_model_call:enter",
        "on_model_call:exit",
        "on_reply:exit",
    ]
    assert "budget: model calls made = 1 (max 1)" in result.stdout
