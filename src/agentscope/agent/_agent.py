"""Minimal multi-turn Agent, preceding the ReAct/tool loop."""

from .._utils._common import _generate_timestamp
from ..message import AssistantMsg, Msg, SystemMsg, ToolCallBlock, Usage
from ..model import ChatModelBase, FinishedReason
from ..state import AgentState


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: ChatModelBase,
        state: AgentState | None = None,
    ) -> None:
        self.name = name
        self._system_prompt = system_prompt
        self.model = model
        self.state = state if state is not None else AgentState()

    async def observe(self, msgs: Msg | list[Msg] | None = None) -> None:
        if msgs is None:
            return
        self.state.context.extend([msgs] if isinstance(msgs, Msg) else msgs)

    async def reply(self, inputs: Msg | list[Msg] | None = None) -> Msg:
        await self.observe(inputs)
        if not self.state.context:
            raise ValueError("Agent needs an input or existing conversation context.")

        messages = [SystemMsg(name="system", content=self._system_prompt), *self.state.context]
        response = await self.model(messages, tools=None)
        if not response.is_last:
            raise NotImplementedError("Streaming responses arrive in stage 5.")
        if response.finished_reason == FinishedReason.INTERRUPTED:
            raise NotImplementedError("Interrupted replies arrive in stage 6.")
        if any(isinstance(block, ToolCallBlock) for block in response.content):
            raise NotImplementedError("Tool execution arrives in stage 4.")

        usage = None
        if response.usage is not None:
            usage = Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_input_tokens=response.usage.cache_input_tokens,
                cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
            )
        reply = AssistantMsg(
            name=self.name,
            content=response.content,
            finished_at=_generate_timestamp(),
            finished_reason="completed",
            usage=usage,
        )
        self.state.context.append(reply)
        return reply
