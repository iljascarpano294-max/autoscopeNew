# -*- coding: utf-8 -*-
"""The vector store abstraction and a process-local implementation."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class VectorDimensionError(Exception):
    """The vector's dimension does not match the store's index."""


@dataclass
class SearchHit:
    """One search result."""

    id: str
    score: float
    metadata: dict[str, Any]


class VectorStoreBase(ABC):
    """Store vectors with ids and metadata; search by cosine similarity."""

    @abstractmethod
    async def upsert(self, id: str, vector: list, metadata: dict[str, Any]) -> None:
        """Insert or replace one vector."""

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Remove one vector; unknown ids are ignored."""

    @abstractmethod
    async def search(self, vector: list, top_k: int) -> list[SearchHit]:
        """Return the top_k most similar vectors, best first."""


class InMemoryVectorStore(VectorStoreBase):
    """Process-local vector store for offline pipelines and tests."""

    def __init__(self, dimensions: int) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be at least 1.")
        self.dimensions = dimensions
        self._vectors: dict[str, tuple[list, dict[str, Any]]] = {}

    async def upsert(self, id: str, vector: list, metadata: dict[str, Any]) -> None:
        if len(vector) != self.dimensions:
            raise VectorDimensionError(
                f"Vector has dimension {len(vector)}, but the store index "
                f"was built with {self.dimensions}; rebuild the index or "
                f"use a matching embedder.",
            )
        self._vectors[id] = (list(vector), dict(metadata))

    async def delete(self, id: str) -> None:
        self._vectors.pop(id, None)

    async def search(self, vector: list, top_k: int) -> list[SearchHit]:
        if len(vector) != self.dimensions:
            raise VectorDimensionError(
                f"Query vector has dimension {len(vector)}, but the store "
                f"index was built with {self.dimensions}.",
            )
        scored = []
        for id, (stored, metadata) in self._vectors.items():
            score = self._cosine(vector, stored)
            if score > 0:
                scored.append(SearchHit(id=id, score=score, metadata=metadata))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
