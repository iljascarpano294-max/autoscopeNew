# -*- coding: utf-8 -*-
"""Console helpers that print an agent event stream to the terminal."""

import sys
from typing import Iterable

from ._renderer import StreamRenderer


def print_stream(events: Iterable, file=None) -> None:
    """Print a stream of agent events (or a single event wrapped in a list)
    to the given file, defaulting to stdout.

    The console only consumes events; it never reads or mutates agent
    state, so it is safe to interleave with any reply_stream consumer.
    """
    renderer = StreamRenderer(file=file)
    for event in events:
        renderer.render(event)


__all__ = ["print_stream", "StreamRenderer"]
