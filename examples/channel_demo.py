"""Stage 12 demo: a Mock channel completes the inbound-to-outbound loop.

The webhook event flows: ChannelEvent -> gateway dedupe/routing ->
ChatService -> agent reply -> channel.send. The same flow a real
channel adapter (Feishu/Discord/DingTalk) runs once credentials exist.
"""

import asyncio

from agentscope.agent import Agent
from agentscope.app._service import ChatService, SessionService
from agentscope.app.channel import ChannelBase, ChannelEvent, ChannelGateway
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


class MockChannel(ChannelBase):
    channel_id = "mock"

    def __init__(self) -> None:
        self.sent: list = []

    async def send(self, target: str, text: str) -> None:
        self.sent.append((target, text))


async def main() -> None:
    sessions = SessionService(
        agent_factory=lambda: Agent(
            "Friday",
            "Prompt",
            FakeChatModel(
                [
                    ChatResponse(content=[TextBlock(text="agent reply")], is_last=True),
                    ChatResponse(content=[TextBlock(text="agent reply")], is_last=True),
                ],
            ),
        ),
    )
    chat = ChatService(sessions)
    gateway = ChannelGateway(sessions=sessions, chat=chat)
    channel = MockChannel()

    event = ChannelEvent(
        channel_id="mock",
        external_user_id="user-1",
        message_id="msg-1",
        text="hello channel",
    )
    session_id = await gateway.receive(event)
    print(f"routed to session: {session_id}")

    reply = sessions.get(session_id).agent.state.context[-1]
    await gateway.send_reply(channel, session_id, reply.get_text_content())
    print(f"delivered: {channel.sent}")

    # A duplicate webhook does not trigger a second agent turn.
    await gateway.receive(event)
    await gateway.receive(event)
    turns = len(sessions.get(session_id).agent.model.calls)
    print(f"turns after duplicate webhook: {turns}")


if __name__ == "__main__":
    asyncio.run(main())
