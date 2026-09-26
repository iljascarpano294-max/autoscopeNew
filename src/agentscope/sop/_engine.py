# -*- coding: utf-8 -*-
"""Running a SOP.

The engine walks the steps in order, hands resumption events to
whichever one parked, and spends the attempt budget. It decides from
each step's :class:`~agentscope.sop.SOPStepRunState` alone, never from
how the step reached it.

Migrated from the reference implementation (commit 5ff52f8), with the
retry handover carrying the last refusal message as feedback.
"""
from itertools import zip_longest
from typing import AsyncGenerator

from ._schema import SOP
from ._state import SOPPhase, SOPRunState, SOPStepRunState
from ..event import (
    AgentEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
)
from ..message import Msg, TextBlock, UserMsg


class SOPEngine:
    """One run of a :class:`~agentscope.sop.SOP`, shaped like an agent.

    Feed it, watch the events, and when something needs a person the
    stream simply ends — nothing stays suspended. Come back with the
    answer and it picks up from the state.
    """

    def __init__(self, sop: SOP, state: SOPRunState | None = None) -> None:
        """Initialize the engine.

        Args:
            sop (`SOP`):
                The procedure to run. Never written to.
            state (`SOPRunState | None`, optional):
                A stored run to carry on from. Omit to start a new one.

        Raises:
            `ValueError`:
                If the state has a different number of steps than the
                SOP, which means the procedure was edited since.
        """
        self.state = state or SOPRunState()
        if self.state.steps and len(self.state.steps) != len(sop.steps):
            raise ValueError(
                f"State has {len(self.state.steps)} steps, but this SOP "
                f"has {len(sop.steps)}. The procedure changed since the "
                f"run was stored; refusing to continue.",
            )
        self.sop = sop
        self.state.steps = [
            step.state_type.model_validate(stored.model_dump())
            if stored is not None
            else step.state_type()
            for step, stored in zip_longest(sop.steps, self.state.steps)
        ]

    @property
    def phase(self) -> SOPPhase:
        """Where the run stands overall."""
        return self.state.phase

    async def reply_stream(
        self,
        inputs: Msg | list[Msg] | UserConfirmResultEvent | UserInterruptEvent | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Run the procedure, streaming what happens.

        Named after :meth:`~agentscope.agent.Agent.reply_stream` so a SOP
        goes wherever an agent goes.

        Args:
            inputs:
                What starts the run, or the answer a parked step was
                waiting for.

        Yields:
            `AgentEvent | Msg`:
                Everything its steps produced on the way.
        """
        interrupting = isinstance(inputs, UserInterruptEvent)
        resuming = interrupting or isinstance(inputs, UserConfirmResultEvent)
        if not resuming and inputs is not None:
            self.state.inputs = (
                [inputs] if isinstance(inputs, Msg) else list(inputs)
            )

        for index, step in enumerate(self.sop.steps):
            record = self.state.steps[index]
            if record.phase is SOPPhase.COMPLETED:
                continue
            if record.phase is SOPPhase.FAILED:
                return

            while True:
                # The answer goes to the step that parked; a fresh
                # attempt gets what the run knows so far.
                if not resuming:
                    record.given = self._handover(index)
                async for event in step.reply_stream(
                    inputs if resuming else record.given,
                    record,
                ):
                    yield event
                inputs, resuming = None, False

                if interrupting:
                    # The parked reply was closed; nothing is retried.
                    return
                if record.phase is SOPPhase.AWAITING:
                    # Let go of the stream rather than hold a coroutine
                    # open; the caller comes back with an answer.
                    return
                if record.phase is SOPPhase.COMPLETED:
                    break
                if len(record.verifications) >= step.max_attempts:
                    record.phase = SOPPhase.FAILED
                    return

    def _handover(self, index: int) -> list[Msg]:
        """What a step is given to work from.

        The run's own inputs for the first step, and what the one before
        handed over for the rest. A retry additionally carries the last
        refusal message as feedback, so the executor knows what to fix.
        """
        own_record = self.state.steps[index]
        if index == 0:
            given = list(self.state.inputs)
        else:
            previous = self.sop.steps[index - 1]
            previous_record = self.state.steps[index - 1]
            given = [
                UserMsg(
                    name="sop",
                    content=[
                        TextBlock(text=f'<handover from="{previous.subject}">'),
                        *(previous_record.submission or []),
                        TextBlock(text="</handover>"),
                    ],
                ),
            ]

        if own_record.verifications and not own_record.verifications[-1].passed:
            refusal = own_record.verifications[-1]
            given.append(
                UserMsg(
                    name="sop",
                    content=[
                        TextBlock(
                            text=(
                                "<feedback>Your previous attempt was "
                                "refused. Fix this and try again: "
                                f"{refusal.message}</feedback>"
                            ),
                        ),
                    ],
                ),
            )
        return given
