"""Stage 12 channel demo smoke test."""

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "channel_demo.py"


def test_channel_demo() -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "routed to session:" in result.stdout
    assert "delivered: [('" in result.stdout
    assert "'agent reply')]" in result.stdout
    # The duplicate webhook never produced a second model call.
    assert "turns after duplicate webhook: 1" in result.stdout
