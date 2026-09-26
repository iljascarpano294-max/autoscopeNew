"""Stage 13 demo: parse, chunk, index, retrieve and cite one document.

The whole pipeline runs offline: a local text file is parsed and
chunked, a keyword fake embedder indexes the chunks, and a
RAGMiddleware injects the retrieved, cited context into the model call.
The fake model echoes what it received so the citations are visible.
"""

import asyncio
import tempfile
from pathlib import Path

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.middleware import RAGMiddleware
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.rag import (
    ApproxTokenChunker,
    KnowledgeBase,
    TextParser,
    InMemoryVectorStore,
)


class KeywordEmbedder:
    """Deterministic fake embedding: one dimension per keyword."""

    dimensions = 3

    def __init__(self, keywords: list) -> None:
        self.keywords = keywords

    def __call__(self, text: str) -> list:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in self.keywords]


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        doc_path = Path(tmp) / "fruit.txt"
        doc_path.write_text(
            "The apple grows on trees in temperate climates. "
            "The banana is long and yellow.",
            encoding="utf-8",
        )

        document = await TextParser().parse(doc_path)
        print(f"parsed: id={document.id} source={document.source}")

        embedder = KeywordEmbedder(["apple", "banana", "cherry"])
        kb = KnowledgeBase(
            vector_store=InMemoryVectorStore(dimensions=embedder.dimensions),
            embedder=embedder,
            chunker=ApproxTokenChunker(chunk_size=32),
        )
        chunk_count = await kb.add_document(document)
        print(f"indexed chunks: {chunk_count}")

        agent = Agent(
            "Friday",
            "Answer with the context if it helps.",
            FakeChatModel(
                [
                    ChatResponse(
                        content=[TextBlock(text="(echoing the retrieved context)")],
                        is_last=True,
                    ),
                ],
            ),
            middlewares=[RAGMiddleware(knowledge_base=kb, top_k=2)],
        )
        reply = await agent.reply(UserMsg("Alice", "tell me about apples"))
        print(f"reply: {reply.get_text_content()}")

        sent = agent.model.calls[0][0]
        for msg in sent:
            if msg.name == "rag_context":
                print(f"injected context:\n{msg.get_text_content()}")


if __name__ == "__main__":
    asyncio.run(main())
