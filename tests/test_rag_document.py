"""Stage 13 task 1: document parsing and chunking."""

import asyncio

import pytest

from agentscope.rag import ApproxTokenChunker, Document, TextParser


def test_parse_and_chunk(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text(
        "AgentScope is a framework. " * 40,  # ~1120 chars
        encoding="utf-8",
    )

    document = asyncio.run(TextParser().parse(source))
    assert document.id == "notes"
    assert document.source == str(source)
    assert document.text.startswith("AgentScope is a framework.")

    chunker = ApproxTokenChunker(chunk_size=50)  # ~200 chars per chunk
    chunks = chunker.split(document)

    assert len(chunks) >= 3
    for index, chunk in enumerate(chunks):
        assert chunk.document_id == document.id
        assert chunk.chunk_id == f"{document.id}:{index}"
        assert chunk.source == document.source
        assert chunk.text
        assert chunk.offset >= 0
    # Offsets are ordered and non-overlapping windows through the text.
    offsets = [chunk.offset for chunk in chunks]
    assert offsets == sorted(offsets)
    assert offsets[1] > offsets[0]

    # An empty document produces no chunks (no empty vectors later).
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    empty_document = asyncio.run(TextParser().parse(empty))
    assert chunker.split(empty_document) == []
