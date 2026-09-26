# -*- coding: utf-8 -*-
"""Plain text document parser."""
from pathlib import Path

from .._document import Document


class TextParser:
    """Parse a UTF-8 text file into a Document."""

    async def parse(self, path: Path | str) -> Document:
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8")
        return Document(
            id=file_path.stem,
            source=str(file_path),
            text=text,
        )
