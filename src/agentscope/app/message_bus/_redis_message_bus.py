# -*- coding: utf-8 -*-
"""Redis-backed message bus (optional; enabled by configuration)."""
from typing import Any

from pydantic import BaseModel

from ._base import MessageBusBase
from ..storage import StorageError


class RedisBusConfig(BaseModel):
    """Configuration for the Redis message bus backend."""

    url: str
    """Connection URL, e.g. ``redis://localhost:6379/0``."""

    @classmethod
    def from_env(cls) -> "RedisBusConfig":
        import os

        url = os.environ.get("AGENTSCOPE_REDIS_URL")
        if not url:
            raise StorageError(
                "The Redis message bus needs the AGENTSCOPE_REDIS_URL "
                "environment variable (e.g. redis://localhost:6379/0).",
            )
        return cls(url=url)


class RedisMessageBus(MessageBusBase):
    """A poll-based bus over Redis lists and sets.

    Publishes push the event onto the topic list and record the event id
    as pending; ``ack`` moves the id to the acked set; ``redeliver``
    re-dispatches pending events. Deduplication works exactly like the
    in-memory bus: one event id is delivered to subscribers once. The
    blocking pub/sub variant of the reference project is a later slice.
    """

    def __init__(self, config: RedisBusConfig) -> None:
        self.config = config
        self._redis = None
        self._subscribers: dict[str, list] = {}

    @classmethod
    def from_env(cls) -> "RedisMessageBus":
        return cls(RedisBusConfig.from_env())

    async def connect(self) -> None:
        import redis.asyncio as aioredis

        try:
            self._redis = aioredis.from_url(
                self.config.url,
                decode_responses=True,
            )
            await self._redis.ping()
        except Exception as error:
            self._redis = None
            raise StorageError(
                f"Redis is unreachable at '{self.config.url}': {error}. "
                f"The error is retriable once the service is back.",
            ) from error

    def _require_connection(self) -> Any:
        if self._redis is None:
            raise StorageError(
                f"The Redis message bus is not connected to "
                f"'{self.config.url}'; call connect() first.",
            )
        return self._redis

    async def publish(self, topic: str, event_id: str, payload: Any) -> None:
        import json

        redis = self._require_connection()
        if await self._redis.sismember(self._acked_key(topic), event_id):
            return
        if await self._redis.sismember(self._pending_key(topic), event_id):
            return
        event = {"event_id": event_id, "payload": json.dumps(payload)}
        async with redis.pipeline(transaction=True) as pipe:
            pipe.sadd(self._pending_key(topic), event_id)
            pipe.rpush(self._topic_key(topic), json.dumps(event))
            await pipe.execute()
        await self._dispatch(topic, event_id, payload)

    async def subscribe(self, topic: str, handler) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    async def ack(self, event_id: str) -> None:
        redis = self._require_connection()
        # The acked marker lives under every topic the id could belong to;
        # event ids are globally unique by contract, so a single global
        # set keeps this simple and correct.
        await self._redis.sadd("bus:acked", event_id)
        for topic in list(self._subscribers):
            await self._redis.srem(self._pending_key(topic), event_id)

    async def redeliver(self) -> None:
        import json

        redis = self._require_connection()
        for topic in list(self._subscribers):
            pending = await self._redis.smembers(self._pending_key(topic))
            acked = await self._redis.smembers("bus:acked")
            for event_id in sorted(pending - acked):
                raw = await self._redis.lrange(
                    self._topic_key(topic),
                    0,
                    -1,
                )
                for item in raw:
                    record = json.loads(item)
                    if record["event_id"] == event_id:
                        await self._dispatch(
                            topic,
                            event_id,
                            json.loads(record["payload"]),
                        )
                        break

    async def _dispatch(self, topic: str, event_id: str, payload: Any) -> None:
        from ._base import BusEvent

        event = BusEvent(topic=topic, event_id=event_id, payload=payload)
        for handler in self._subscribers.get(topic, []):
            await handler(event)

    @staticmethod
    def _topic_key(topic: str) -> str:
        return f"bus:topic:{topic}"

    @staticmethod
    def _pending_key(topic: str) -> str:
        return f"bus:pending:{topic}"

    @staticmethod
    def _acked_key(topic: str) -> str:
        return "bus:acked"
