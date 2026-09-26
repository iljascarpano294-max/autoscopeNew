"""Stage 13 task 3: the RAG middleware injecting retrieved context."""

import asyncio

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.middleware import RAGMiddleware
from agentscope.rag import Document, KnowledgeBase
from agentscope.rag._vdb import InMemoryVectorStore


class KeywordEmbedder:
    dimensions = 3

    def __init__(self, keywords: list) -> None:
        self.keywords = keywords

    def __call__(self, text: str) -> list:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in self.keywords]


def _agent(middlewares) -> Agent:
    return Agent(
        "Friday",
        "Answer with the context if it helps.",
        FakeChatModel(
            [ChatResponse(content=[TextBlock(text="assembled answer")], is_last=True)],
        ),
        middlewares=middlewares,
    )


def _kb_with_fruit_doc() -> KnowledgeBase:
    embedder = KeywordEmbedder(["apple", "banana", "cherry"])
    kb = KnowledgeBase(
        vector_store=InMemoryVectorStore(dimensions=3),
        embedder=embedder,
    )
    asyncio.run(
        kb.add_document(
            Document(
                id="fruit-doc",
                source="/docs/fruit.txt",
                text="The apple grows on trees in temperate climates.",
            ),
        ),
    )
    return kb


def test_rag_answer_injects_cited_context() -> None:
    kb = _kb_with_fruit_doc()
    agent = _agent([RAGMiddleware(knowledge_base=kb, top_k=2)])

    asyncio.run(agent.reply(UserMsg("Alice", "tell me about apples")))

    sent = agent.model.calls[0][0]
    rag_messages = [msg for msg in sent if msg.name == "rag_context"]
    assert len(rag_messages) == 1
    context_text = rag_messages[0].get_text_content()
    # The retrieved chunk and its citation reach the model.
    assert "apple" in context_text
    assert "/docs/fruit.txt" in context_text
    # The original user message is preserved after the injected context.
    assert sent[-1].get_text_content() == "tell me about apples"
    assert sent[-1].name == "Alice"


def test_no_results_adds_no_fake_context() -> None:
    kb = _kb_with_fruit_doc()
    agent = _agent([RAGMiddleware(knowledge_base=kb, top_k=2)])

    asyncio.run(agent.reply(UserMsg("Alice", "explain quantum physics")))

    sent = agent.model.calls[0][0]
    assert not [msg for msg in sent if msg.name == "rag_context"]
    assert sent[-1].get_text_content() == "explain quantum physics"
