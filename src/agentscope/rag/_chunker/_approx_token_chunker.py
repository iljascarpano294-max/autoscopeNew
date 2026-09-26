# -*- coding: utf-8 -*-
"""Approximate-token chunker: split documents without a tokenizer."""
from .._document import Chunk, Document

_CHARS_PER_TOKEN = 4


class ApproxTokenChunker:
    """Split a document into chunks of roughly ``chunk_size`` tokens.

    Uses an average character-per-token ratio instead of a tokenizer, so
    the pipeline works offline; word boundaries are respected where
    possible and each chunk records its character offset for citations.
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 0) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1.")
        if not 0 <= overlap < chunk_size:
            raise ValueError("overlap must be within [0, chunk_size).")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, document: Document) -> list[Chunk]:
        """Split the document; empty documents yield no chunks."""
        text = document.text
        if not text.strip():
            return []

        max_chars = self.chunk_size * _CHARS_PER_TOKEN
        step = max_chars - self.overlap * _CHARS_PER_TOKEN

        chunks: list[Chunk] = []
        offset = 0
        seq = 0
        while offset < len(text):
            end = min(offset + max_chars, len(text))
            # Prefer breaking at a word boundary inside the window.
            if end < len(text):
                boundary = text.rfind(" ", offset + 1, end)
                if boundary > offset:
                    end = boundary
            piece = text[offset:end].strip()
            if piece:
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        chunk_id=f"{document.id}:{seq}",
                        source=document.source,
                        seq=seq,
                        text=piece,
                        offset=offset,
                    ),
                )
                seq += 1
            if end >= len(text):
                break
            offset = offset + step if step > 0 else end
        return chunks
