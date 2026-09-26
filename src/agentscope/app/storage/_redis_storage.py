# -*- coding: utf-8 -*-
"""Redis-backed session storage (optional; enabled by configuration)."""
import json
from typing import Any, Callable

from pydantic import BaseModel

from ...message import Msg
from ...state import AgentState
from ._base import StorageBase, StorageError


class RedisStorageConfig(BaseModel):
    """Configuration for the Redis storage backend."""

    url: str
    """Connection URL, e.g. ``redis://localhost:6379/0``. Credentials
    belong in the environment or a local secret store, never in code."""

    @classmethod
    def from_env(cls) -> "RedisStorageConfig":
        import os

        url = os.environ.get("AGENTSCOPE_REDIS_URL")
        if not url:
            raise StorageError(
                "Redis storage needs the AGENTSCOPE_REDIS_URL environment "
                "variable (e.g. redis://localhost:6379/0).",
            )
        return cls(url=url)


class RedisStorage(StorageBase):
    """Store sessions in Redis as JSON documents.

    The backend is only used when explicitly configured; every
    connection problem surfaces as a StorageError naming the target so
    the caller can retry.
    """

    def __init__(self, config: RedisStorageConfig) -> None:
        self.config = config
        self._redis = None

    @classmethod
    def from_env(cls) -> "RedisStorage":
        return cls(RedisStorageConfig.from_env())

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
                f"Redis storage is not connected to '{self.config.url}'; "
                f"call connect() first.",
            )
        return self._redis

    async def save_session(self, record: Any) -> None:
        redis = self._require_connection()
        state = record.agent.state
        state_meta = state.model_dump(exclude={"context"})
        try:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.hset(
                    f"session:{record.session_id}",
                    mapping={
                        "agent_id": record.agent_id,
                        "reply_id": state.reply_id,
                        "state_meta": json.dumps(state_meta),
                        "created_at": record.created_at,
                        "last_active_at": record.last_active_at,
                    },
                )
                await pipe.execute()
        except Exception as error:
            raise StorageError(
                f"Redis write failed for session "
                f"'{record.session_id}': {error}",
            ) from error

    async def load_session(
        self,
        session_id: str,
        agent_factory: Callable[[], Any] | None = None,
    ) -> Any:
        redis = self._require_connection()
        data = await redis.hgetall(f"session:{session_id}")
        if not data:
            from ..._service import SessionNotFound

            raise SessionNotFound(
                f"Session '{session_id}' was not found in storage.",
            )
        if agent_factory is None:
            raise StorageError(
                "load_session requires an agent_factory to rebuild the "
                "session's agent.",
            )
        context_keys = sorted(await redis.lrange(f"session:{session_id}:messages", 0, -1))
        try:
            context = [Msg.model_validate_json(raw) for raw in context_keys]
            state_meta = json.loads(data["state_meta"])
        except (json.JSONDecodeError, ValueError) as error:
            raise StorageError(
                f"Stored session '{session_id}' is corrupted: {error}",
            ) from error
        agent = agent_factory()
        agent.state = AgentState(
            context=context,
            reply_id=data.get("reply_id", ""),
            middle_context=state_meta.get("middle_context", {}),
        )
        from ..._service import SessionRecord

        return SessionRecord(
            session_id=session_id,
            agent_id=data["agent_id"],
            agent=agent,
            created_at=data["created_at"],
            last_active_at=data["last_active_at"],
        )

    async def append_message(self, session_id: str, msg: Msg) -> None:
        redis = self._require_connection()
        try:
            payload = msg.model_dump_json()
        except Exception as error:
            raise StorageError(f"Failed to serialize message: {error}") from error
        try:
            await redis.rpush(f"session:{session_id}:messages", payload)
        except Exception as error:
            raise StorageError(
                f"Redis append failed for session '{session_id}': {error}",
            ) from error

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
        self._redis = None
