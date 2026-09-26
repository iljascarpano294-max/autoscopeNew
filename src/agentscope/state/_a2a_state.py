# -*- coding: utf-8 -*-
"""State for A2A (agent-to-agent) conversations."""
from pydantic import BaseModel, Field

from .._utils._common import _generate_id


class A2AState(BaseModel):
    """What one A2A agent keeps about its peer and its calls.

    Seen message ids back the idempotency guarantee: a repeated inbound
    message id replays the stored answer instead of triggering another
    remote action.
    """

    model_config = {"arbitrary_types_allowed": True}

    task_id: str = Field(default_factory=_generate_id)
    """Correlation id shared by this agent's calls to the peer."""

    reply_id: str = Field(default_factory=_generate_id)
    """Identity of the reply in progress."""

    peer_endpoint: str
    """The remote agent's endpoint URL."""

    seen_message_ids: set[str] = Field(default_factory=set)
    """Message ids already sent to the peer."""

    cached_replies: dict[str, str] = Field(default_factory=dict)
    """message_id -> reply text, so duplicates replay without a call."""
