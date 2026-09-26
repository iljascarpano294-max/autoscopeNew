"""Compare import-visible names of the reconstruction against
docs/compatibility-matrix.md and print the differences.

Usage: python scripts/check_public_api.py
Exit code 0 when every entry marked 已对齐 is importable, 1 otherwise.
"""

import importlib
import re
import sys
from pathlib import Path

MATRIX = Path(__file__).resolve().parent.parent / "docs" / "compatibility-matrix.md"

ROW = re.compile(r"^\|\s*([a-zA-Z_.]+)\s*\|\s*([A-Za-z_]+)\s*\|\s*(已对齐|部分对齐|暂缓)\s*\|")


def load_matrix() -> list[tuple[str, str, str]]:
    rows = []
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if match:
            rows.append((match.group(1), match.group(2), match.group(3)))
    return rows


def main() -> int:
    rows = load_matrix()
    aligned = [(module, name) for module, name, status in rows if status == "已对齐"]
    deferred = [(module, name) for module, name, status in rows if status != "已对齐"]

    missing: list[tuple[str, str]] = []
    for module, name in aligned:
        try:
            package = importlib.import_module(module)
        except ImportError as error:
            missing.append((module, f"<import failed: {error}>"))
            continue
        if not hasattr(package, name):
            missing.append((module, name))

    print(f"matrix entries: {len(rows)} (aligned: {len(aligned)}, partial/deferred: {len(deferred)})")
    for module, name in missing:
        print(f"MISSING: {module}.{name}")
    if missing:
        print("audit FAILED")
        return 1
    print("audit OK: every aligned name is importable")
    print("deferred (not yet migrated), by module:")
    for module, name in deferred:
        print(f"  {module}: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
