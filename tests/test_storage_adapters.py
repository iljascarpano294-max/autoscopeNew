"""Stage 11 task 4: optional Redis backends, created from environment."""

import asyncio
import os

import pytest

from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import RedisStorage, StorageError


def test_missing_env_config_is_readable(monkeypatch) -> None:
    monkeypatch.delenv("AGENTSCOPE_REDIS_URL", raising=False)

    with pytest.raises(StorageError, match="AGENTSCOPE_REDIS_URL"):
        RedisStorage.from_env()

    with pytest.raises(StorageError, match="AGENTSCOPE_REDIS_URL"):
        RedisMessageBus.from_env()


def test_unreachable_redis_reports_retriable_error(monkeypatch) -> None:
    # A port with nothing listening: connection fails fast and the error
    # names the target so the operator can retry or fix the config.
    monkeypatch.setenv("AGENTSCOPE_REDIS_URL", "redis://127.0.0.1:59999/0")

    async def run():
        storage = RedisStorage.from_env()
        try:
            await storage.save_session(record=None)
        except StorageError as error:
            return "59999" in str(error) or "unreachable" in str(error).lower()
        return False

    assert asyncio.run(run()) is True


@pytest.mark.skipif(
    not os.environ.get("AGENTSCOPE_REDIS_URL"),
    reason="set AGENTSCOPE_REDIS_URL to run the live Redis integration",
)
def test_live_redis_roundtrip() -> None:
    async def run():
        storage = RedisStorage.from_env()
        await storage.connect()
        await storage.close()

    asyncio.run(run())
