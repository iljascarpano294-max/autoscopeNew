# -*- coding: utf-8 -*-
"""Document and chunk models for the RAG pipeline."""
from pydantic import BaseModel, Field


class Document(BaseModel):
    """One parsed source document."""

    id: str
    """Stable document identifier used as the idempotency key on import."""

    source: str
    """Where the content came from (file path, URL, ...), kept for
    citations."""

    text: str
    """The full document text."""


class Chunk(BaseModel):
    """One piece of a document, with a citable position."""

    document_id: str
    """The document this chunk belongs to."""

    chunk_id: str = ""
    """``document_id:seq``; the idempotency key in the vector store."""

    source: str
    """Inherited from the document, for displayable citations."""

    seq: int
    """The chunk's position in the document."""

    text: str
    """The chunk text."""

    offset: int = 0
    """The character offset of the chunk start in the document text."""
