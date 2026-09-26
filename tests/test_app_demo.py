"""Stage 10 app demo smoke test."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "app_demo.py"


def test_app_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "created session:" in result.stdout
    assert "reply: Hello from the agent." in result.stdout
    # After shutdown the in-process session is gone: 404.
    assert "after restart: 404 (session is gone)" in result.stdout
