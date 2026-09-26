# -*- coding: utf-8 -*-
"""Budget control middleware for AgentScope agents."""
from typing import AsyncGenerator, Callable, TYPE_CHECKING

from ..event import ReplyEndEvent, ReplyStartEvent
from ._base import MiddlewareBase

if TYPE_CHECKING:
    from ..agent import Agent


class BudgetMiddleware(MiddlewareBase):
    """Middleware that enforces a hard limit on model calls per reply.

    Stage 7 keeps the plan-specified call-count budget: every
    ``on_model_call`` records one usage unit keyed by the reply id in
    ``agent.state.middle_context`` and raises once the budget is
    exhausted, so no further model request is issued.

    Budget state lives in the agent's state, never on the middleware
    instance, so one instance can be shared by several agents without
    sharing counters. A fresh reply (new reply_id) starts a new budget
    window; the counter is removed when the reply ends.
    """

    def __init__(self, max_model_calls: int) -> None:
        """Initialize the budget middleware.

        Args:
            max_model_calls (`int`):
                Maximum number of model calls allowed per reply. The
                (max_model_calls + 1)-th call raises RuntimeError.
        """
        if max_model_calls < 1:
            raise ValueError("max_model_calls must be at least 1.")
        self.max_model_calls = max_model_calls

    async def on_reply(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Clean up the per-reply counter when the reply ends."""
        middleware_key = await self.get_middleware_key()

        async for event in next_handler(**input_kwargs):
            if isinstance(event, ReplyEndEvent):
                agent.state.middle_context.get(middleware_key, {}).pop(
                    event.reply_id,
                    None,
                )
            yield event

    async def on_model_call(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable,
    ):
        """Count the call and block the request once the budget is used up."""
        middleware_key = await self.get_middleware_key()
        reply_id = agent.state.reply_id

        used = agent.state.middle_context.get(middleware_key, {}).get(reply_id, 0)
        if used >= self.max_model_calls:
            raise RuntimeError(
                f"Model call budget exhausted: this reply already used "
                f"{used} of {self.max_model_calls} allowed model calls.",
            )
        agent.state.middle_context.setdefault(middleware_key, {})[reply_id] = used + 1

        return await next_handler(**input_kwargs)
