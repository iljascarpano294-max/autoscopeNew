# -*- coding: utf-8 -*-
"""The base pipeline protocol."""

from typing import AsyncGenerator, Protocol, runtime_checkable

from ..event import (
    AgentEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
)
from ..message import Msg


@runtime_checkable
class PipelineProtocol(Protocol):
    """What a pipeline has to offer to go where an agent goes.

    Declared as a plain ``def`` returning an async generator rather than
    an ``async def``: such a function is called, not awaited, and an
    ``async def`` here would be satisfied by neither ``Agent`` nor any
    pipeline.
    """

    def reply_stream(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Reply to the given inputs and stream what happens."""
