# -*- coding: utf-8 -*-
"""Attribute whitelisting: what may reach a span, and what may not."""
from typing import Any

_SENSITIVE_KEY_MARKERS = ("api_key", "apikey", "password", "secret", "token", "credential")

_ALLOWED_ATTRIBUTE_KEYS = frozenset(
    {
        "agent",
        "model",
        "tool",
        "tool_input_keys",
        "reply_id",
        "session_id",
        "event_type",
        "status",
        "exit_code",
        "timed_out",
    },
)


def safe_attributes(**kwargs: Any) -> dict[str, Any]:
    """Filter kwargs down to the whitelisted attribute names.

    Tool inputs, message text and anything that looks like a credential
    are never recorded — the span notes the *names* of tool input keys,
    not their values.
    """
    safe: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in _ALLOWED_ATTRIBUTE_KEYS:
            safe[key] = value
        elif any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS):
            safe[key] = "[REDACTED]"
    return safe


def redact_secrets(text: str, secrets: list[str]) -> str:
    """Replace every occurrence of the given secret values in ``text``."""
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted
