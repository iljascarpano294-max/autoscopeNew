"""Conversation state for the minimal stage 3 Agent."""

from pydantic import BaseModel, Field

from ..message import Msg


class AgentState(BaseModel):
    context: list[Msg] = Field(default_factory=list)
