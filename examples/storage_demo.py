"""Stage 11 demo: sessions survive a restart through SQLite storage.

Two "processes" (two service instances over one database file) share a
session: the first writes two turns, the second restores the session and
continues the conversation with the old history intact.
"""

import asyncio
import tempfile
from pathlib import Path

from agentscope.agent import Agent
from agentscope.app._service import ChatService, SessionService
from agentscope.app.storage import SQLiteStorage
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


def _factory(responses: list) -> "callable":
    def build() -> Agent:
        return Agent("Friday", "Be concise", FakeChatModel(responses))

    return build


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sessions.db"

        # --- process 1: create a session and chat for two turns ---
        storage = SQLiteStorage(db_path)
        sessions = SessionService(
            agent_factory=_factory(
                [
                    ChatResponse(content=[TextBlock(text="first reply")], is_last=True),
                    ChatResponse(content=[TextBlock(text="second reply")], is_last=True),
                ],
            ),
            storage=storage,
        )
        chat = ChatService(sessions)
        session_id = sessions.create(agent_id="demo").session_id
        print(f"session: {session_id}")
        reply = await chat.send(session_id, "question one")
        print(f"turn 1: {reply.get_text_content()}")
        reply = await chat.send(session_id, "question two")
        print(f"turn 2: {reply.get_text_content()}")
        await storage.close()

        # --- process 2: restore and continue ---
        storage = SQLiteStorage(db_path)
        sessions = SessionService(
            agent_factory=_factory(
                [ChatResponse(content=[TextBlock(text="third reply")], is_last=True)],
            ),
            storage=storage,
        )
        chat = ChatService(sessions)
        record = await sessions.load(session_id)
        print(f"restored history: {len(record.agent.state.context)} messages")
        reply = await chat.send(session_id, "question three")
        print(f"turn 3: {reply}")
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
