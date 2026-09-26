# -*- coding: utf-8 -*-
"""The SOP schema: steps, and the procedure they compose.

Migrated from the reference implementation (commit 5ff52f8), with a
trimmed agent-driven step: one call is one attempt, the final message
becomes the submission, and an injected verifier files the verdict.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Awaitable, Callable

from ..event import (
    AgentEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
)
from ..message import DataBlock, Msg, TextBlock
from ._state import SOPPhase, SOPStepRunState, VerificationResult


class SOPStepBase(ABC):
    """One milestone: a name, what it must prove, and how many tries.

    Subclasses put whatever they like in :meth:`reply_stream` — the
    contract is only that **one call is one attempt**, and that it either
    parks or files a verdict on the state it was handed.
    """

    state_type: type[SOPStepRunState] = SOPStepRunState
    """What this step's run state looks like. Subclass
    :class:`~agentscope.sop.SOPStepRunState` and name it here when a step
    has to remember more than the base fields."""

    def __init__(
        self,
        subject: str,
        description: str,
        max_attempts: int = 3,
    ) -> None:
        """Initialize the step.

        Args:
            subject (`str`):
                A brief, actionable name.
            description (`str`):
                What this step must achieve — the destination, not the
                route.
            max_attempts (`int`, defaults to `3`):
                How many refusals before the run gives up on it. Enforced
                by the engine, not here.
        """
        self.subject = subject
        self.description = description
        self.max_attempts = max_attempts

    @abstractmethod
    def reply_stream(
        self,
        inputs: Msg | list[Msg] | UserConfirmResultEvent | UserInterruptEvent | None,
        state: SOPStepRunState,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Make one attempt at this step, streaming what happens.

        Args:
            inputs:
                What the engine handed over for a fresh attempt, or the
                answer a parked attempt was waiting for.
            state (`SOPStepRunState`):
                This step's record in the run. Read it to pick up where
                the last call stopped; write its phase, submission and
                verdicts as the attempt goes.

        Yields:
            `AgentEvent | Msg`:
                What the attempt does as it does it.
        """


@dataclass
class SOP:
    """A standard operating procedure: an ordered list of steps."""

    name: str
    """A short name for the procedure."""

    steps: list[SOPStepBase] = field(default_factory=list)
    """The steps, executed in this order."""


class SOPStep(SOPStepBase):
    """A step executed by an agent-like pipeline.

    One call is one attempt: the executor's ``reply_stream`` runs to its
    end (or parks), the final message becomes the submission, and the
    injected verifier files a verdict on the state. When no final message
    arrives the attempt parks (``AWAITING``); the answer that resumes it
    is routed back by the engine.
    """

    def __init__(
        self,
        executor: Callable[..., AsyncGenerator[AgentEvent | Msg, None]],
        subject: str,
        description: str = "",
        max_attempts: int = 3,
        verify: Callable[
            [list[Msg], list[TextBlock | DataBlock]],
            Awaitable[VerificationResult | bool] | VerificationResult | bool,
        ]
        | None = None,
    ) -> None:
        """Initialize the step.

        Args:
            executor:
                An object with ``reply_stream`` (an Agent, or any
                PipelineProtocol).
            subject (`str`):
                A brief, actionable name.
            description (`str`):
                What this step must achieve.
            max_attempts (`int`):
                How many refusals before the run gives up on it.
            verify:
                An optional verifier called with ``(given, submission)``
                that returns a :class:`VerificationResult` or a bool.
                Defaults to accepting every attempt.
        """
        super().__init__(subject, description, max_attempts)
        self.executor = executor
        self._verify = verify

    async def _verdict(
        self,
        given: list[Msg],
        submission: list[TextBlock | DataBlock],
    ) -> VerificationResult:
        from .._utils._common import _execute_async_or_sync_func

        if self._verify is None:
            return VerificationResult(
                passed=True,
                message="",
                verifier=self.subject,
            )
        result = await _execute_async_or_sync_func(self._verify, given, submission)
        if isinstance(result, VerificationResult):
            return result
        return VerificationResult(passed=bool(result), verifier=self.subject)

    def reply_stream(  # pylint: disable=invalid-overridden-method
        self,
        inputs: Msg | list[Msg] | UserConfirmResultEvent | UserInterruptEvent | None,
        state: SOPStepRunState,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        return self._attempt(inputs, state)

    async def _attempt(
        self,
        inputs: Msg | list[Msg] | UserConfirmResultEvent | UserInterruptEvent | None,
        state: SOPStepRunState,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        state.phase = SOPPhase.RUNNING
        final_msg = None
        async for item in self.executor.reply_stream(inputs):
            if isinstance(item, Msg):
                final_msg = item
            else:
                yield item

        if final_msg is None:
            # The executor parked (e.g. a tool confirmation): the attempt
            # stays open until the answer comes back through the engine.
            state.phase = SOPPhase.AWAITING
            state.submission = None
            return

        submission = [
            block
            for block in final_msg.content
            if isinstance(block, (TextBlock, DataBlock))
        ]
        state.submission = submission
        verdict = await self._verdict(list(state.given), submission)
        state.verifications.append(verdict)
        state.phase = SOPPhase.COMPLETED if verdict.passed else SOPPhase.PENDING
