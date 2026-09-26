"""Stage 12 task 1: channel events, routing and the gateway."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.app._service import ChatService, SessionService
from agentscope.app.channel import ChannelBase, ChannelEvent, ChannelGateway
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, FakeChatModel


class MockChannel(ChannelBase):
    """Records outbound sends; fails when the target says 'fail'."""

    channel_id = "mock"

    def __init__(self) -> None:
        self.sent: list = []
        self.fail_targets: set = set()

    async def send(self, target: str, text: str) -> None:
        if target in self.fail_targets:
            raise RuntimeError("outbound endpoint down")
        self.sent.append((target, text))


def _service() -> tuple:
    def factory():
        return Agent(
            "Friday",
            "Prompt",
            FakeChatModel(
                [
                    ChatResponse(content=[TextBlock(text="agent reply")], is_last=True),
                    ChatResponse(content=[TextBlock(text="agent reply")], is_last=True),
                ],
            ),
        )

    sessions = SessionService(agent_factory=factory)
    return sessions, ChatService(sessions)


def test_route_and_dedupe() -> None:
    sessions, chat = _service()
    gateway = ChannelGateway(sessions=sessions, chat=chat)

    async def run():
        # Same user on the same channel maps to one session.
        first = ChannelEvent(
            channel_id="mock",
            external_user_id="u1",
            message_id="m1",
            text="hello",
        )
        session_1a = await gateway.receive(first)
        same_again = ChannelEvent(
            channel_id="mock",
            external_user_id="u1",
            message_id="m2",
            text="again",
        )
        session_1b = await gateway.receive(same_again)

        # The same user on a different channel gets a separate session.
        other_channel = ChannelEvent(
            channel_id="feishu",
            external_user_id="u1",
            message_id="m3",
            text="hello",
        )
        session_2 = await gateway.receive(other_channel)

        # A duplicate webhook (same message_id) must not trigger a second
        # chat turn.
        calls_before = len(gateway._chat._locks)  # noqa: SLF001 - test probe
        duplicate = ChannelEvent(
            channel_id="mock",
            external_user_id="u1",
            message_id="m1",
            text="hello",
        )
        session_dup = await gateway.receive(duplicate)

        return session_1a, session_1b, session_2, session_dup, calls_before

    s1a, s1b, s2, sdup, _ = asyncio.run(run())

    assert s1a == s1b  # same user + channel → same session
    assert s2 != s1a  # different channel → isolated session
    assert sdup == s1a  # duplicate returns the same session...
    # ...but the agent saw only two turns, not three.
    record = sessions.get(s1a)
    assert len(record.agent.model.calls) == 2


def test_outbound_failure_keeps_retry_state() -> None:
    sessions, chat = _service()
    channel = MockChannel()
    gateway = ChannelGateway(sessions=sessions, chat=chat)

    async def run():
        event = ChannelEvent(
            channel_id="mock",
            external_user_id="u1",
            message_id="m1",
            text="hello",
        )
        session_id = await gateway.receive(event)
        channel.fail_targets.add(session_id)

        await gateway.send_reply(channel, session_id, "agent reply")
        pending = gateway.pending_outbound()
        status_before_retry = pending[0].status

        # The endpoint recovers; the retry succeeds and clears the queue.
        channel.fail_targets.clear()
        await gateway.retry_outbound()
        return channel.sent, pending, status_before_retry, gateway.pending_outbound()

    sent, pending, status_before_retry, remaining = asyncio.run(run())

    assert pending and pending[0].text == "agent reply"
    assert status_before_retry == "failed"
    assert remaining == []
    assert sent == [(pending[0].target, "agent reply")]
