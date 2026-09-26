"""Stage 13 task 4: cross-session long-term memory, isolated per user."""

import asyncio

import pytest

from agentscope.middleware._longterm_memory import (
    LocalLongTermMemory,
    LongTermMemoryMiddleware,
)


def test_memory_isolation() -> None:
    memory = LongTermMemoryMiddleware(backend=LocalLongTermMemory())

    # Session 1: user A writes a fact.
    asyncio.run(memory.save("user-a", "likes apples"))
    asyncio.run(memory.save("user-a", "works night shifts"))

    # Session 2 (a new conversation, same middleware): user A recalls it.
    facts_a = asyncio.run(memory.recall("user-a", "apple"))
    assert facts_a == ["likes apples"]
    facts_a_shift = asyncio.run(memory.recall("user-a", "shift"))
    assert facts_a_shift == ["works night shifts"]

    # User B never sees user A's private memories.
    facts_b = asyncio.run(memory.recall("user-b", "apple"))
    assert facts_b == []


def test_memory_injects_into_model_call() -> None:
    from agentscope.agent import Agent
    from agentscope.message import TextBlock, UserMsg
    from agentscope.model import ChatResponse, FakeChatModel

    memory = LongTermMemoryMiddleware(backend=LocalLongTermMemory())
    asyncio.run(memory.save("Alice", "prefers answers about apples"))

    agent = Agent(
        "Friday",
        "Prompt",
        FakeChatModel(
            [ChatResponse(content=[TextBlock(text="ok")], is_last=True)],
        ),
        middlewares=[memory],
    )
    asyncio.run(agent.reply(UserMsg("Alice", "tell me about apples")))

    sent = agent.model.calls[0][0]
    memory_messages = [msg for msg in sent if msg.name == "long_term_memory"]
    assert len(memory_messages) == 1
    assert "prefers answers about apples" in memory_messages[0].get_text_content()


def test_mem0_adapter_requires_config() -> None:
    from agentscope.middleware._longterm_memory import Mem0LongTermMemoryMiddleware

    with pytest.raises(Exception, match="mem0"):
        Mem0LongTermMemoryMiddleware()


def test_mem0_adapter_is_replaceable() -> None:
    """Any backend with save/recall works behind the same middleware."""

    class DictBackend:
        def __init__(self) -> None:
            self.store: dict = {}

        async def save(self, user_id: str, fact: str) -> None:
            self.store.setdefault(user_id, []).append(fact)

        async def recall(self, user_id: str, query: str) -> list:
            return [f for f in self.store.get(user_id, []) if query in f]

    backend = DictBackend()
    memory = LongTermMemoryMiddleware(backend=backend)
    asyncio.run(memory.save("user-a", "custom backend fact"))

    facts = asyncio.run(memory.recall("user-a", "custom"))
    assert facts == ["custom backend fact"]
