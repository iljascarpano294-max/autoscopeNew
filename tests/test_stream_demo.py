"""Stage 5 stream demo smoke test."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "stream_demo.py"


def test_stream_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "2 + 3 equals 5." in result.stdout
    assert "[tool add]" in result.stdout
