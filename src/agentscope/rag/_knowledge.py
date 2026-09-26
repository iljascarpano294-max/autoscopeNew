# -*- coding: utf-8 -*-
"""The knowledge base: parse -> chunk -> embed -> retrieve."""
from dataclasses import dataclass
from typing import Callable

from ._chunker import ApproxTokenChunker
from ._document import Chunk, Document
from ._vdb import VectorStoreBase


@dataclass
class RetrievedChunk:
    """One retrieved chunk with its citable position."""

    chunk: Chunk
    score: float
    chunk_id: str
    """Shortcut to ``chunk.chunk_id`` for citation rendering."""


class KnowledgeBase:
    """Index documents and retrieve chunks relevant to a query.

    Chunk ids are ``document_id:seq``, so re-importing the same document
    (same id, same content version) overwrites in place instead of
    duplicating index records; deleting a document removes all of its
    chunks.
    """

    def __init__(
        self,
        vector_store: VectorStoreBase,
        embedder: Callable[[str], list],
        chunker: ApproxTokenChunker | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedder = embedder
        self.chunker = chunker or ApproxTokenChunker()
        self._doc_chunks: dict[str, list[str]] = {}

    async def add_document(self, document: Document) -> int:
        """Chunk, embed and index a document. Returns the chunk count."""
        chunks = self.chunker.split(document)
        chunk_ids = []
        for chunk in chunks:
            vector = self.embedder(chunk.text)
            await self.vector_store.upsert(
                chunk.chunk_id,
                vector,
                metadata={
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "seq": chunk.seq,
                    "offset": chunk.offset,
                    "text": chunk.text,
                },
            )
            chunk_ids.append(chunk.chunk_id)
        # Re-importing the same document overwrites its chunks in place.
        self._doc_chunks[document.id] = chunk_ids
        return len(chunks)

    async def delete_document(self, document_id: str) -> None:
        """Remove every chunk belonging to the document."""
        for chunk_id in self._doc_chunks.pop(document_id, []):
            await self.vector_store.delete(chunk_id)

    async def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """Retrieve the most relevant chunks; unrelated queries return
        nothing rather than fabricating citations."""
        vector = self.embedder(query)
        hits = await self.vector_store.search(vector, top_k)
        results = []
        for hit in hits:
            chunk = Chunk(
                document_id=hit.metadata["document_id"],
                chunk_id=hit.id,
                source=hit.metadata["source"],
                seq=hit.metadata["seq"],
                text=hit.metadata["text"],
                offset=hit.metadata["offset"],
            )
            results.append(RetrievedChunk(chunk=chunk, score=hit.score, chunk_id=hit.id))
        return results
