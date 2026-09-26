"""Stage 11 task 3: the message bus contract and in-memory delivery."""

import asyncio

import pytest

from agentscope.app.message_bus import InMemoryMessageBus


def test_bus_delivery() -> None:
    async def run():
        bus = InMemoryMessageBus()
        received: list = []
        acked: set = set()

        async def handler(event):
            received.append(event)
            # Only ack the first delivery; the handler "crashes" otherwise.
            if event.payload.get("ok"):
                acked.add(event.event_id)
                await bus.ack(event.event_id)

        await bus.subscribe("tasks", handler)

        # Two distinct events, two different topics.
        await bus.publish("tasks", "evt-1", {"ok": True})
        await bus.publish("tasks", "evt-2", {"ok": False})
        await bus.publish("other", "evt-3", {"ok": True})

        # A duplicate publish of the same event id is not delivered again.
        await bus.publish("tasks", "evt-1", {"ok": True})

        topics_seen = [event.topic for event in received]
        return received, acked, topics_seen

    received, acked, topics_seen = asyncio.run(run())

    # evt-1 delivered exactly once despite the duplicate publish.
    assert [event.event_id for event in received] == ["evt-1", "evt-2"]
    # Topic isolation: the 'other' subscriber topic never leaked in.
    assert set(topics_seen) == {"tasks"}
    assert acked == {"evt-1"}


def test_unacked_events_can_be_redelivered() -> None:
    async def run():
        bus = InMemoryMessageBus()
        deliveries: list = []

        async def handler(event):
            deliveries.append(event.event_id)

        await bus.subscribe("tasks", handler)
        await bus.publish("tasks", "evt-1", {"n": 1})

        # No ack: the pending event can be redelivered (retry semantics).
        await bus.redeliver()
        first_round = list(deliveries)

        await bus.ack("evt-1")
        await bus.redeliver()
        second_round = list(deliveries)

        return first_round, second_round

    first_round, second_round = asyncio.run(run())

    assert first_round == ["evt-1", "evt-1"]  # redelivered, still unacked
    assert second_round == ["evt-1", "evt-1"]  # acked: no further delivery


def test_duplicate_event_id_never_runs_twice_after_ack() -> None:
    """A non-idempotent consumer must not run twice for one event."""

    async def run():
        bus = InMemoryMessageBus()
        processed: list = []

        async def handler(event):
            processed.append(event.event_id)
            await bus.ack(event.event_id)

        await bus.subscribe("tasks", handler)
        await bus.publish("tasks", "evt-9", {"n": 1})
        await bus.publish("tasks", "evt-9", {"n": 1})
        await bus.redeliver()
        await bus.publish("tasks", "evt-9", {"n": 1})
        return processed

    processed = asyncio.run(run())
    assert processed == ["evt-9"]
