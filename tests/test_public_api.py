"""Stage 16 task 4: every name marked 已对齐 in the compatibility matrix
must be importable."""

import importlib
import re
from pathlib import Path

MATRIX = Path(__file__).resolve().parent.parent / "docs" / "compatibility-matrix.md"

ROW = re.compile(r"^\|\s*([a-zA-Z_.]+)\s*\|\s*([A-Za-z_]+)\s*\|\s*(已对齐|部分对齐|暂缓)\s*\|")


def _aligned_rows() -> list[tuple[str, str]]:
    rows = []
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if match and match.group(3) == "已对齐":
            rows.append((match.group(1), match.group(2)))
    assert rows, "the compatibility matrix must contain aligned entries"
    return rows


def test_matrix_aligned_names_are_importable() -> None:
    missing = []
    for module_name, attr in _aligned_rows():
        package = importlib.import_module(module_name)
        if not hasattr(package, attr):
            missing.append(f"{module_name}.{attr}")
    assert missing == [], f"aligned but not importable: {missing}"


def test_matrix_deferred_entries_are_documented() -> None:
    """The deferred list must stay honest: known gaps stay recorded."""
    rows = []
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if match:
            rows.append(match.group(3))
    assert "暂缓" in rows
    assert "已对齐" in rows
