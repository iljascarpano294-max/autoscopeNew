# -*- coding: utf-8 -*-
"""Minimal plain-text renderer for agent event streams.

The stage-5 console only renders; it never touches agent state. The rich
based interactive renderer of the reference project arrives with the
channel/Web-UI stages.
"""
from ..event import (
    ReplyStartEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
)
from ..message import Msg


class StreamRenderer:
    """Render agent events as plain terminal text.

    Text deltas are written exactly as they arrive; the final message
    object is silent because its text has already been streamed as deltas.
    """

    def __init__(self, file=None) -> None:
        self._file = file

    def _write(self, text: str) -> None:
        import sys

        target = self._file if self._file is not None else sys.stdout
        target.write(text)
        target.flush()

    def render(self, event) -> None:
        """Render one event; unknown event types are ignored."""
        if isinstance(event, ReplyStartEvent):
            self._write(f"[{event.name}] ")
        elif isinstance(event, TextBlockDeltaEvent):
            self._write(event.delta)
        elif isinstance(event, TextBlockEndEvent):
            self._write("\n")
        elif isinstance(event, ToolResultStartEvent):
            self._write(f"[tool {event.tool_call_name}] ")
        elif isinstance(event, ToolResultTextDeltaEvent):
            self._write(event.delta)
        elif isinstance(event, ToolResultEndEvent):
            self._write(f" ({event.state})\n")
        elif isinstance(event, Msg):
            # The final message's text was already streamed as deltas;
            # repeating it here would print everything twice.
            pass
