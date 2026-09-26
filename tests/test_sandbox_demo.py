"""Stage 14 sandbox demo smoke test (offline local mode)."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sandbox_demo.py"


def test_sandbox_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "read back: 'sandbox demo'" in result.stdout
    assert "mode: local" in result.stdout
