"""Conversation state for the minimal Agent (stages 3-4)."""

from typing import Sequence

from pydantic import BaseModel, Field

from .._utils._common import _generate_id
from ..message import (
    DataBlock,
    HintBlock,
    Msg,
    TextBlock,
    ToolCallBlock,
    ToolCallState,
    ToolResultBlock,
)


class AgentState(BaseModel):
    context: list[Msg] = Field(default_factory=list)
    reply_id: str = Field(default_factory=_generate_id)
    """Identity of the reply in progress; assistant blocks produced by one
    reply are merged into the message carrying this id."""

    def append_context(
        self,
        name: str,
        blocks: Sequence[
            TextBlock | DataBlock | HintBlock | ToolCallBlock | ToolResultBlock
        ],
    ) -> None:
        """Append the given blocks to the agent's own message with the current
        `reply_id`. If such message doesn't exist, a new assistant message
        with agent's name and current reply ID will be created.
        """
        # If append to the latest message
        if (
            self.context
            and self.context[-1].role == "assistant"
            and self.context[-1].name == name
            and self.context[-1].id == self.reply_id
        ):
            self.context[-1].content.extend(blocks)
        else:
            # Create a new assistant message with the current reply ID
            self.context.append(
                Msg(
                    id=self.reply_id,
                    role="assistant",
                    name=name,
                    content=list(blocks),
                ),
            )

    def get_awaiting_tool_calls(self, name: str) -> list[ToolCallBlock]:
        """Get the tail assistant message's tool calls still awaiting an
        outside response — currently the ``ASKING`` user confirmation
        state written by the agent's permission gate.

        Args:
            name (`str`):
                Only messages authored by this agent name are inspected;
                observed messages from other agents are ignored.

        Returns:
            `list[ToolCallBlock]`:
                The awaiting tool call blocks, empty if none.
        """
        if not self.context:
            return []
        last_msg = self.context[-1]
        if last_msg.role != "assistant" or last_msg.name != name:
            return []
        return [
            tc
            for tc in last_msg.get_content_blocks("tool_call")
            if tc.state == ToolCallState.ASKING
        ]
