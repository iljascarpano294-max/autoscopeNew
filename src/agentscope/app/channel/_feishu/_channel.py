# -*- coding: utf-8 -*-
"""The Feishu (Lark) channel adapter.

Stage 12 keeps a deterministic verification contract: the webhook
signature is HMAC-SHA256 over ``"{timestamp}:{payload}"`` keyed with the
app secret, and timestamps outside the tolerance window are refused
before anything reaches the agent. Real Feishu callbacks use their
proprietary AES encryption scheme; swapping the verifier in is a
drop-in change (manual acceptance with real credentials is a separate
step — no credentials are ever read in tests).
"""
import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from .._base import ChannelBase, ChannelEvent

_TIMESTAMP_TOLERANCE_SECONDS = 300


class ChannelVerificationError(Exception):
    """An inbound webhook failed signature or timestamp verification."""


class FeishuChannel(ChannelBase):
    """Receive Feishu webhook events and deliver replies to a webhook."""

    channel_id = "feishu"

    def __init__(
        self,
        app_secret: str,
        webhook_url: str,
        client: httpx.AsyncClient | None = None,
        timestamp_tolerance: int = _TIMESTAMP_TOLERANCE_SECONDS,
    ) -> None:
        self.app_secret = app_secret
        self.webhook_url = webhook_url
        self._client = client or httpx.AsyncClient()
        self.timestamp_tolerance = timestamp_tolerance

    def verify(
        self,
        payload: str,
        signature: str,
        timestamp: str,
    ) -> ChannelEvent:
        """Verify the webhook and normalize it into a ChannelEvent.

        Args:
            payload (`str`):
                The raw request body.
            signature (`str`):
                The HMAC-SHA256 hex digest of ``"{timestamp}:{payload}"``
                keyed with the app secret.
            timestamp (`str`):
                The unix timestamp the signature was computed over.

        Raises:
            `ChannelVerificationError`:
                On a stale timestamp or a signature mismatch.
        """
        try:
            stamp = int(timestamp)
        except ValueError as error:
            raise ChannelVerificationError(
                "Invalid webhook timestamp.",
            ) from error
        if abs(time.time() - stamp) > self.timestamp_tolerance:
            raise ChannelVerificationError(
                "Webhook timestamp is outside the tolerance window; "
                "refusing the event (replay protection).",
            )

        expected = self._sign(timestamp, payload)
        if not hmac.compare_digest(expected, signature or ""):
            raise ChannelVerificationError(
                "Webhook signature mismatch; refusing the event.",
            )

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ChannelVerificationError(
                f"Webhook payload is not valid JSON: {error}",
            ) from error
        return ChannelEvent(
            channel_id=self.channel_id,
            external_user_id=str(data.get("user_id", "")),
            message_id=str(data.get("message_id", "")),
            text=str(data.get("text", "")),
            metadata=data,
        )

    def _sign(self, timestamp: str, payload: str) -> str:
        message = f"{timestamp}:{payload}".encode()
        return hmac.new(
            self.app_secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

    async def send(self, target: str, text: str) -> None:
        """Deliver one text message to a Feishu chat."""
        response = await self._client.post(
            self.webhook_url,
            json={
                "target": target,
                "msg_type": "text",
                "content": {"text": text},
            },
        )
        response.raise_for_status()
