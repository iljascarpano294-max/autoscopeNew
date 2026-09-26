# -*- coding: utf-8 -*-
"""TracingMiddleware: one span per reply, model call and tool call."""
from .._base import MiddlewareBase
from ._attributes import safe_attributes
from ._setup import get_tracer


class TracingMiddleware(MiddlewareBase):
    """Create parent-child spans across the reply lifecycle.

    ``agent.reply`` is the root; ``model.call`` and ``tool.call`` spans
    hang off the currently open span, so one request keeps a stable
    parent-child chain. Only whitelisted attributes are recorded — tool
    inputs and credentials never reach a span. Every span is closed even
    when the wrapped call raises, with the error attached.
    """

    async def on_reply(self, agent, input_kwargs, next_handler):
        tracer = get_tracer()
        span = tracer.start_span(
            "agent.reply",
            safe_attributes(agent=agent.name),
        )
        try:
            async for item in next_handler(**input_kwargs):
                yield item
        except Exception as error:
            tracer.end_span(span, error=f"{type(error).__name__}: {error}")
            raise
        tracer.end_span(span)

    async def on_model_call(self, agent, input_kwargs, next_handler):
        tracer = get_tracer()
        current_model = input_kwargs.get("current_model")
        span = tracer.start_span(
            "model.call",
            safe_attributes(
                model=getattr(current_model, "model", "unknown"),
            ),
        )
        try:
            result = await next_handler(**input_kwargs)
        except Exception as error:
            tracer.end_span(span, error=f"{type(error).__name__}: {error}")
            raise
        tracer.end_span(span)
        return result

    async def on_acting(self, agent, input_kwargs, next_handler):
        tracer = get_tracer()
        tool_call = input_kwargs.get("tool_call")
        span = tracer.start_span(
            "tool.call",
            # The input *values* never reach the span, only the tool name.
            safe_attributes(tool=tool_call.name),
        )
        try:
            async for item in next_handler(**input_kwargs):
                yield item
        except Exception as error:
            tracer.end_span(span, error=f"{type(error).__name__}: {error}")
            raise
        tracer.end_span(span)
