# -*- coding: utf-8 -*-
"""A minimal goal-driven pipeline over named members.

Stage 9 keeps the plan-specified slice: a goal description and an ordered
list of members (any PipelineProtocol); the goal starts the first member,
each later member receives the previous member's result as a handover,
and a member failure surfaces as a traceable CustomEvent instead of
ending the run silently. Dynamic member addition is process-internal
state; team services and databases arrive with the app stages.
"""
from typing import AsyncGenerator

from ..event import AgentEvent, CustomEvent
from ..message import Msg, TextBlock, UserMsg


class GoalPipeline:
    """Drive a list of members towards one goal, in order."""

    def __init__(self, goal: str, members: list) -> None:
        """Initialize the pipeline.

        Args:
            goal (`str`):
                A description of what the run must achieve; it opens the
                first member's input.
            members (`list`):
                The members, in execution order. Every member must satisfy
                the pipeline protocol; each keeps its own context.
        """
        if not members:
            raise ValueError("A goal pipeline needs at least one member.")
        self.goal = goal
        self.members = list(members)

    def reply_stream(
        self,
        inputs: Msg | list[Msg] | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        return self._run(inputs)

    async def _run(
        self,
        inputs: Msg | list[Msg] | None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        yield CustomEvent(
            name="GOAL_STARTED",
            value={
                "goal": self.goal,
                "members": [getattr(member, "name", type(member).__name__) for member in self.members],
            },
        )

        current: Msg | list[Msg] | None = inputs
        run_result: Msg | None = None
        for member in self.members:
            if current is None:
                current = UserMsg(name="user", content=self.goal)
            try:
                final_msg = None
                async for item in member.reply_stream(current):
                    if isinstance(item, Msg):
                        final_msg = item
                    else:
                        yield item
            except Exception as error:  # noqa: BLE001 - reported, not swallowed
                yield CustomEvent(
                    name="MEMBER_FAILED",
                    value={
                        "member": getattr(member, "name", type(member).__name__),
                        "error": str(error),
                    },
                )
                return

            if final_msg is None:
                # The member parked (e.g. on a tool confirmation); pass the
                # resumption through when the caller comes back.
                return
            run_result = final_msg
            member_name = getattr(member, "name", type(member).__name__)
            current = UserMsg(
                name="goal",
                content=[
                    TextBlock(text=f'<result from="{member_name}">'),
                    *final_msg.content,
                    TextBlock(text="</result>"),
                ],
            )

        yield run_result
