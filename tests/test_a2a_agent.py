"""Stage 15 task 1: the A2A agent over a mock transport."""

import asyncio

import pytest

from agentscope.agent import A2AAgent
from agentscope.message import TextBlock, UserMsg


class MockTransport:
    """The remote side: counts calls, can be slow."""

    def __init__(self, reply: str = "remote answer", delay: float = 0) -> None:
        self.reply = reply
        self.delay = delay
        self.requests: list = []

    async def __call__(self, request: dict) -> dict:
        self.requests.append(request)
        await asyncio.sleep(self.delay)
        return {"text": self.reply, "task_id": request["message_id"]}


def test_a2a_mock() -> None:
    transport = MockTransport()
    agent = A2AAgent(endpoint="http://peer", transport=transport)

    async def run():
        events, final = [], None
        async for item in agent.reply_stream(UserMsg("Alice", "hello peer")):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item)
        return events, final

    events, final = asyncio.run(run())

    # The remote reply arrives as the final message.
    assert final is not None and final.get_text_content() == "remote answer"
    assert final.finished_reason == "completed"
    # The request carried correlation ids and the user text.
    assert transport.requests[0]["text"] == "hello peer"
    assert transport.requests[0]["message_id"]
    assert events  # reply lifecycle events still stream


def test_duplicate_message_id_runs_once() -> None:
    transport = MockTransport()
    agent = A2AAgent(endpoint="http://peer", transport=transport)
    message = UserMsg("Alice", "hello peer", id="fixed-msg-id")

    async def run():
        first = None
        async for item in agent.reply_stream(message):
            if item.__class__.__name__ == "Msg":
                first = item
        # The exact same message again.
        second = None
        async for item in agent.reply_stream(message):
            if item.__class__.__name__ == "Msg":
                second = item
        return first, second

    first, second = asyncio.run(run())

    # The remote side was called once; the duplicate replayed the answer.
    assert len(transport.requests) == 1
    assert first is not None and second is not None
    assert second.get_text_content() == first.get_text_content()


def test_remote_timeout_terminates() -> None:
    transport = MockTransport(delay=5)
    agent = A2AAgent(endpoint="http://peer", transport=transport, timeout=0.05)

    async def run():
        events, final = [], None
        async for item in agent.reply_stream(UserMsg("Alice", "hello")):
            if item.__class__.__name__ == "Msg":
                final = item
            else:
                events.append(item.type)
        return events, final

    events, final = asyncio.run(run())

    # The stream terminates instead of hanging: a failed ReplyEnd arrives
    # and there is no final message.
    assert "REPLY_END" in events
    assert final is None
    end_index = events.index("REPLY_END")
    assert events[end_index] == "REPLY_END"
