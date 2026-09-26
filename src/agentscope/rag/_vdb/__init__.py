# -*- coding: utf-8 -*-
"""Vector store adapters."""

from ._vector_store import InMemoryVectorStore, SearchHit, VectorDimensionError, VectorStoreBase

__all__ = [
    "InMemoryVectorStore",
    "SearchHit",
    "VectorDimensionError",
    "VectorStoreBase",
]
