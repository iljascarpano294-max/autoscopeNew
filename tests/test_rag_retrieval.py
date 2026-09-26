"""Stage 13 task 2: vector store and knowledge base retrieval."""

import asyncio

import pytest

from agentscope.rag import ApproxTokenChunker, Document, TextParser
from agentscope.rag._knowledge import KnowledgeBase
from agentscope.rag._vdb import InMemoryVectorStore


class KeywordEmbedder:
    """Deterministic fake embedding: one dimension per keyword."""

    dimensions = 3

    def __init__(self, keywords: list) -> None:
        self.keywords = keywords

    def __call__(self, text: str) -> list:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in self.keywords]


def _knowledge_base() -> KnowledgeBase:
    embedder = KeywordEmbedder(["apple", "banana", "cherry"])
    return KnowledgeBase(
        vector_store=InMemoryVectorStore(dimensions=3),
        embedder=embedder,
        chunker=ApproxTokenChunker(chunk_size=64),
    )


def test_retrieve_citation() -> None:
    kb = _knowledge_base()

    document = Document(
        id="fruit-doc",
        source="/docs/fruit.txt",
        text="The apple grows on trees. The banana is long and yellow.",
    )
    asyncio.run(kb.add_document(document))

    results = asyncio.run(kb.retrieve("tell me about apples", top_k=2))

    # The most relevant chunk ranks first and carries a citable source.
    assert results
    assert "apple" in results[0].chunk.text.lower()
    assert results[0].chunk.source == "/docs/fruit.txt"
    assert results[0].chunk.chunk_id == results[0].chunk_id
    assert results[0].score > 0

    # Re-importing the same document never duplicates index records.
    asyncio.run(kb.add_document(document))
    results_after_reimport = asyncio.run(kb.retrieve("apple", top_k=10))
    ids = [result.chunk.chunk_id for result in results_after_reimport]
    assert len(ids) == len(set(ids))

    # Deleting the document empties retrieval for its content.
    asyncio.run(kb.delete_document("fruit-doc"))
    assert asyncio.run(kb.retrieve("apple", top_k=5)) == []


def test_dimension_mismatch_is_rejected() -> None:
    store = InMemoryVectorStore(dimensions=3)
    with pytest.raises(Exception, match="dimension"):
        asyncio.run(store.upsert("x", [1.0, 2.0], {"source": "s"}))


def test_unrelated_query_returns_no_fake_citation() -> None:
    kb = _knowledge_base()
    asyncio.run(
        kb.add_document(
            Document(id="fruit-doc", source="/docs/fruit.txt", text="The apple grows on trees."),
        ),
    )
    # A query with no keyword overlap scores zero and returns nothing —
    # the pipeline never fabricates citations.
    results = asyncio.run(kb.retrieve("quantum physics", top_k=3))
    assert results == []
