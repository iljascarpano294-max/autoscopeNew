"""Stage 12 task 2: the Feishu channel adapter (verification + send)."""

import asyncio
import hashlib
import hmac
import json
import time

import httpx
import pytest

from agentscope.app.channel import FeishuChannel


def _sign(secret: str, timestamp: str, payload: str) -> str:
    message = f"{timestamp}:{payload}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _valid_payload() -> str:
    return json.dumps(
        {"user_id": "u-42", "message_id": "msg-1", "text": "hello feishu"},
    )


def test_feishu_verify() -> None:
    sent: list = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"code": 0})

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    channel = FeishuChannel(
        app_secret="test-secret",
        webhook_url="https://open.feishu.example/hook",
        client=client,
    )

    now = str(int(time.time()))
    payload = _valid_payload()
    good_signature = _sign("test-secret", now, payload)

    # A valid signature and fresh timestamp produce a ChannelEvent.
    event = channel.verify(payload, good_signature, now)
    assert event.channel_id == "feishu"
    assert event.external_user_id == "u-42"
    assert event.message_id == "msg-1"
    assert event.text == "hello feishu"

    # A wrong signature is rejected.
    with pytest.raises(Exception, match="signature"):
        channel.verify(payload, "0" * 64, now)

    # An expired timestamp is rejected even with a correct signature.
    stale = str(int(time.time()) - 10_000)
    stale_signature = _sign("test-secret", stale, payload)
    with pytest.raises(Exception, match="timestamp"):
        channel.verify(payload, stale_signature, stale)

    # The outbound send maps text into the Feishu message shape.
    asyncio.run(channel.send("chat-77", "the reply"))
    assert sent == [
        {
            "target": "chat-77",
            "msg_type": "text",
            "content": {"text": "the reply"},
        },
    ]
