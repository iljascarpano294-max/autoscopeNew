# -*- coding: utf-8 -*-
"""Long-term memory: local storage slice and optional adapters."""
from abc import ABC, abstractmethod


class LongTermMemoryBackendBase(ABC):
    """A per-user fact store behind the long-term memory middleware."""

    @abstractmethod
    async def save(self, user_id: str, fact: str) -> None:
        """Store one fact for the user."""

    @abstractmethod
    async def recall(self, user_id: str, query: str) -> list[str]:
        """Return the user's facts relevant to the query."""


class LocalLongTermMemory(LongTermMemoryBackendBase):
    """Process-local per-user fact store.

    Facts never cross user boundaries: each user id owns an isolated
    list, and recall searches only that user's facts.
    """

    def __init__(self) -> None:
        self._facts: dict[str, list[str]] = {}

    async def save(self, user_id: str, fact: str) -> None:
        self._facts.setdefault(user_id, []).append(fact)

    async def recall(self, user_id: str, query: str) -> list[str]:
        """Recall the user's facts sharing a word with the query — a
        keyword stand-in for semantic search."""
        query_words = {
            word.strip(".,!?").lower()
            for word in query.split()
            if len(word.strip(".,!?")) >= 3
        }
        return [
            fact
            for fact in self._facts.get(user_id, [])
            if any(word in fact.lower() for word in query_words)
        ]
