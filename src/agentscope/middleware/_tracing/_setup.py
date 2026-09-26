# -*- coding: utf-8 -*-
"""Tracer setup and exporters."""
import contextvars
from dataclasses import dataclass, field
from typing import Any

from ..._utils._common import _generate_id, _generate_timestamp


@dataclass
class Span:
    """One traced operation with its position in the span tree."""

    name: str
    span_id: str = field(default_factory=_generate_id)
    parent_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_generate_timestamp)
    ended: bool = False
    error: str | None = None


class InMemoryExporter:
    """Collect finished spans in memory (tests and local inspection)."""

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def export(self, span: Span) -> None:
        self.spans.append(span)


class NullExporter:
    """Drop spans: tracing configured but nothing recorded."""

    def export(self, span: Span) -> None:
        return None


class Metrics:
    """Counters for model/tool calls, failures and latency."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.model_calls = 0
        self.model_failures = 0
        self.total_model_latency_ms = 0.0
        self.tool_calls = 0
        self.tool_failures = 0

    def record_model_call(self, duration_ms: float, failed: bool) -> None:
        self.model_calls += 1
        self.total_model_latency_ms += duration_ms
        if failed:
            self.model_failures += 1

    def record_tool_call(self, failed: bool) -> None:
        self.tool_calls += 1
        if failed:
            self.tool_failures += 1


class Tracer:
    """Create nested spans; the current span is task-local context.

    Ending a span restores its parent as the current span, so siblings
    under the same parent get a stable parent-child chain.
    """

    def __init__(self, exporter: Any = None) -> None:
        self.exporter = exporter or NullExporter()
        self.metrics = Metrics()
        self._current: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
            f"span-{id(self)}",
            default=None,
        )
        self._tokens: dict[str, contextvars.Token] = {}

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Span:
        parent = self._current.get()
        span = Span(
            name=name,
            parent_id=parent.span_id if parent else None,
            attributes=dict(attributes or {}),
        )
        self._tokens[span.span_id] = self._current.set(span)
        return span

    def end_span(self, span: Span, error: str | None = None) -> None:
        span.ended = True
        span.error = error
        self.exporter.export(span)
        token = self._tokens.pop(span.span_id, None)
        if token is not None:
            self._current.reset(token)

    @property
    def current(self) -> Span | None:
        return self._current.get()


_tracer: Tracer | None = None


def setup_tracing(exporter: Any = None) -> Tracer:
    """Configure the global tracer with the given exporter.

    Args:
        exporter (`Any`, optional):
            Receives every finished span via ``export(span)``. Defaults
            to a null exporter, so calling with no configuration is
            harmless.
    """
    global _tracer
    _tracer = Tracer(exporter)
    return _tracer


def get_tracer() -> Tracer:
    """The global tracer; a null-export tracer when setup was skipped."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer(NullExporter())
    return _tracer


def get_metrics() -> Metrics:
    """The global tracer's metrics counters."""
    return get_tracer().metrics
