"""Minimal Agent with the stage 4 reasoning-acting tool loop."""

from .._utils._common import _generate_id, _generate_timestamp
from ..message import (
    AssistantMsg,
    Msg,
    SystemMsg,
    ToolCallBlock,
    ToolResultBlock,
    ToolCallState,
    Usage,
)
from ..model import ChatModelBase, FinishedReason
from ..state import AgentState
from ..tool import ToolResponse, Toolkit


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: ChatModelBase,
        state: AgentState | None = None,
        toolkit: Toolkit | None = None,
        max_iters: int = 10,
    ) -> None:
        self.name = name
        self._system_prompt = system_prompt
        self.model = model
        self.state = state if state is not None else AgentState()
        self.toolkit = toolkit
        if max_iters < 1:
            raise ValueError("max_iters must be at least 1.")
        self._max_iters = max_iters

    async def observe(self, msgs: Msg | list[Msg] | None = None) -> None:
        if msgs is None:
            return
        self.state.context.extend([msgs] if isinstance(msgs, Msg) else msgs)

    async def reply(self, inputs: Msg | list[Msg] | None = None) -> AssistantMsg:
        await self.observe(inputs)
        if not self.state.context:
            raise ValueError("Agent needs an input or existing conversation context.")

        self.state.reply_id = _generate_id()
        finished_reason = "completed"
        for _ in range(self._max_iters):
            response = await self._reasoning()
            if not response.is_last:
                raise NotImplementedError("Streaming responses arrive in stage 5.")
            if response.finished_reason == FinishedReason.INTERRUPTED:
                raise NotImplementedError("Interrupted replies arrive in stage 6.")

            tool_calls = [
                block for block in response.content if isinstance(block, ToolCallBlock)
            ]
            if tool_calls and self.toolkit is None:
                raise NotImplementedError("Tool execution arrives in stage 4.")

            self._save_to_context(response.content, usage=response.usage)
            if not tool_calls:
                break
            await self._acting(tool_calls)
        else:
            # Every round ended with tool calls; stop instead of looping forever.
            finished_reason = "exceed_max_iters"

        reply_msg = self.state.context[-1]
        reply_msg.finished_at = _generate_timestamp()
        reply_msg.finished_reason = finished_reason
        return reply_msg

    async def _reasoning(self):
        messages = [
            SystemMsg(name="system", content=self._system_prompt),
            *self.state.context,
        ]
        tools = (
            await self.toolkit.get_tool_schemas() if self.toolkit is not None else None
        )
        return await self.model(messages, tools=tools)

    async def _acting(self, tool_calls: list[ToolCallBlock]) -> None:
        """Execute the tool calls of the current round in request order and
        save one ToolResultBlock per call into the context."""
        for tool_call in tool_calls:
            async for item in self.toolkit.call_tool(tool_call, self.state):
                if isinstance(item, ToolResponse):
                    self._save_to_context(
                        [
                            ToolResultBlock(
                                id=tool_call.id,
                                name=tool_call.name,
                                output=item.content,
                                state=item.state,
                                metadata=item.metadata,
                            ),
                        ],
                    )
                    self._update_tool_call_state(
                        tool_call.id,
                        ToolCallState.FINISHED,
                    )

    def _save_to_context(self, blocks: list, usage=None) -> None:
        msg_usage = None
        if usage is not None:
            msg_usage = Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_input_tokens=usage.cache_input_tokens or 0,
                cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
            )
        if not blocks and msg_usage is None:
            return
        self.state.append_context(self.name, blocks)
        if msg_usage is not None:
            self.state.context[-1].append_usage(msg_usage)

    def _update_tool_call_state(self, tool_call_id: str, state: ToolCallState) -> None:
        if not self.state.context:
            return
        last_msg = self.state.context[-1]
        if last_msg.role != "assistant" or last_msg.name != self.name:
            return
        for block in last_msg.content:
            if isinstance(block, ToolCallBlock) and block.id == tool_call_id:
                block.state = state
