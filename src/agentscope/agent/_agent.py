"""Minimal Agent: stages 4-6 tool loop, event streaming, permissions."""

import inspect
import json
from typing import Any, AsyncGenerator

from .._utils._common import _generate_id, _generate_timestamp
from ..event import (
    AgentEvent,
    ModelCallEndEvent,
    ModelCallStartEvent,
    ReplyEndEvent,
    ReplyStartEvent,
    RequireUserConfirmEvent,
    TextBlockDeltaEvent,
    TextBlockEndEvent,
    TextBlockStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
    UserConfirmResultEvent,
    UserInterruptEvent,
)
from ..message import (
    Msg,
    SystemMsg,
    TextBlock,
    ToolCallBlock,
    ToolResultBlock,
    ToolCallState,
    ToolResultState,
    Usage,
)
from ..model import ChatModelBase
from ..permission import PermissionBehavior, PermissionEngine
from ..state import AgentState
from ..tool import ToolResponse, Toolkit
from ..types import ReplyFinishedReason


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: ChatModelBase,
        state: AgentState | None = None,
        toolkit: Toolkit | None = None,
        max_iters: int = 10,
        permission_engine: PermissionEngine | None = None,
    ) -> None:
        self.name = name
        self._system_prompt = system_prompt
        self.model = model
        self.state = state if state is not None else AgentState()
        self.toolkit = toolkit
        self.permission_engine = permission_engine
        if max_iters < 1:
            raise ValueError("max_iters must be at least 1.")
        self._max_iters = max_iters

    async def observe(self, msgs: Msg | list[Msg] | None = None) -> None:
        if msgs is None:
            return
        self.state.context.extend([msgs] if isinstance(msgs, Msg) else msgs)

    async def reply(self, inputs: Msg | list[Msg] | None = None) -> Msg:
        """Non-streaming entry: run the same reply stream and return only
        the final message."""
        final_msg = None
        async for item in self.reply_stream(inputs):
            if isinstance(item, Msg):
                final_msg = item
        if final_msg is None:
            raise RuntimeError("The reply stream ended without a final message.")
        return final_msg

    async def reply_stream(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Run one reasoning-acting reply, yield events as they happen, and
        finish with exactly one final Msg. A parked (ASK) confirmation ends
        the stream on RequireUserConfirmEvent; pass a UserConfirmResultEvent
        to resume, or a UserInterruptEvent to abort it."""
        if isinstance(inputs, UserInterruptEvent):
            async for item in self._handle_interrupt(inputs):
                yield item
            return

        if isinstance(inputs, UserConfirmResultEvent):
            if not self.state.context:
                raise ValueError(
                    "Agent needs an existing conversation context to resume.",
                )
            yield ReplyStartEvent(reply_id=self.state.reply_id, name=self.name)
            async for item in self._apply_confirm_results(inputs):
                yield item
            async for item in self._reasoning_acting_loop():
                yield item
            return

        await self.observe(inputs)
        if not self.state.context:
            raise ValueError("Agent needs an input or existing conversation context.")

        self.state.reply_id = _generate_id()
        yield ReplyStartEvent(reply_id=self.state.reply_id, name=self.name)
        async for item in self._reasoning_acting_loop():
            yield item

    async def _reasoning_acting_loop(self) -> AsyncGenerator[AgentEvent | Msg, None]:
        """The reasoning-acting loop shared by fresh and resumed replies."""
        finished_reason = ReplyFinishedReason.COMPLETED
        for _ in range(self._max_iters):
            # ----- Reasoning: one model call, streamed as events -----
            yield ModelCallStartEvent(
                reply_id=self.state.reply_id,
                model_name=self.model.model,
            )
            messages = [
                SystemMsg(name="system", content=self._system_prompt),
                *self.state.context,
            ]
            tools = (
                await self.toolkit.get_tool_schemas()
                if self.toolkit is not None
                else None
            )
            res = await self.model(messages, tools=tools)

            block_ids: dict = {"text": None, "tools": []}
            completed_response = None
            if inspect.isasyncgen(res):
                async for chunk in res:
                    if chunk.is_last:
                        completed_response = chunk
                    else:
                        async for event in self._convert_chat_response_to_event(
                            block_ids,
                            chunk,
                        ):
                            yield event
            else:
                completed_response = res
                async for event in self._convert_chat_response_to_event(
                    block_ids,
                    res,
                ):
                    yield event

            # Close the streams that are still open.
            if block_ids["text"] is not None:
                yield TextBlockEndEvent(
                    reply_id=self.state.reply_id,
                    block_id=block_ids["text"],
                )
                block_ids["text"] = None
            for tool_call_id in list(block_ids["tools"]):
                yield ToolCallEndEvent(
                    reply_id=self.state.reply_id,
                    tool_call_id=tool_call_id,
                )
            block_ids["tools"] = []

            if completed_response is None:
                raise RuntimeError(
                    "Model returned an empty streaming response: no "
                    "is_last=True chunk was received.",
                )
            usage = completed_response.usage
            yield ModelCallEndEvent(
                reply_id=self.state.reply_id,
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cache_input_tokens=getattr(usage, "cache_input_tokens", 0) or 0,
                cache_creation_input_tokens=(
                    getattr(usage, "cache_creation_input_tokens", 0) or 0
                ),
                finished_reason=completed_response.finished_reason,
            )

            tool_calls = [
                block
                for block in completed_response.content
                if isinstance(block, ToolCallBlock)
            ]
            if tool_calls and self.toolkit is None:
                raise NotImplementedError("Tool execution arrives in stage 4.")

            # ----- Persist the completed model call exactly once -----
            self._save_to_context(
                completed_response.content,
                usage=completed_response.usage,
            )
            if not tool_calls:
                break

            # ----- Acting: execute tool calls, stream their results -----
            parked = False
            async for event in self._acting(tool_calls):
                if isinstance(event, RequireUserConfirmEvent):
                    parked = True
                yield event
            if parked:
                # The reply parks on user confirmation: the stream ends
                # here and resumes with a UserConfirmResultEvent.
                return
        else:
            # Every round ended with tool calls; stop instead of looping forever.
            finished_reason = ReplyFinishedReason.EXCEED_MAX_ITERS

        reply_msg = self.state.context[-1]
        reply_msg.finished_at = _generate_timestamp()
        reply_msg.finished_reason = finished_reason
        yield ReplyEndEvent(
            reply_id=self.state.reply_id,
            finished_reason=finished_reason,
        )
        yield reply_msg

    async def _apply_confirm_results(
        self,
        event: UserConfirmResultEvent,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Validate and apply a user confirmation event against the parked
        tool calls; confirmed calls then execute exactly once."""
        pending = self.state.get_awaiting_tool_calls(self.name)
        pending_ids = {tc.id for tc in pending}
        extra_ids = [
            confirmation.tool_call.id
            for confirmation in event.confirm_results
            if confirmation.tool_call.id not in pending_ids
        ]
        if extra_ids:
            raise ValueError(
                f"Received UserConfirmResultEvent with tool call ids "
                f"{extra_ids} that are not waiting for confirmation.",
            )

        confirmed_calls = []
        for confirmation in event.confirm_results:
            if confirmation.confirmed:
                self._update_tool_call_state(
                    confirmation.tool_call.id,
                    ToolCallState.ALLOWED,
                )
                confirmed_calls.append(confirmation.tool_call)
            else:
                async for evt in self._error_tool_result(
                    confirmation.tool_call,
                    (
                        "<system-reminder>The execution of tool "
                        f'"{confirmation.tool_call.name}" is denied by user!'
                        "</system-reminder>"
                    ),
                    ToolResultState.DENIED,
                ):
                    yield evt

        # Confirmed calls run without re-checking permissions.
        for tool_call in confirmed_calls:
            async for evt in self._acting([tool_call], skip_permission=True):
                yield evt

    async def _handle_interrupt(
        self,
        event: UserInterruptEvent,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Close every pending tool call with an interrupted result and end
        the reply without entering the reasoning-acting loop."""
        reply_msg = None
        if self.state.context:
            last_msg = self.state.context[-1]
            if last_msg.role == "assistant" and last_msg.name == self.name:
                reply_msg = last_msg
            for tool_call in self.state.get_awaiting_tool_calls(self.name):
                async for evt in self._error_tool_result(
                    tool_call,
                    (
                        "<system-reminder>The tool call has been "
                        "interrupted by the user.</system-reminder>"
                    ),
                    ToolResultState.INTERRUPTED,
                ):
                    yield evt

        yield ReplyEndEvent(
            reply_id=event.reply_id,
            finished_reason=ReplyFinishedReason.INTERRUPTED,
        )
        if reply_msg is not None:
            reply_msg.finished_at = _generate_timestamp()
            reply_msg.finished_reason = ReplyFinishedReason.INTERRUPTED
            yield reply_msg

    async def _error_tool_result(
        self,
        tool_call: ToolCallBlock,
        message: str,
        state: ToolResultState,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Record a failure result for a tool call without executing it."""
        yield ToolResultStartEvent(
            reply_id=self.state.reply_id,
            tool_call_id=tool_call.id,
            tool_call_name=tool_call.name,
        )
        self._save_to_context(
            [
                ToolResultBlock(
                    id=tool_call.id,
                    name=tool_call.name,
                    output=message,
                    state=state,
                ),
            ],
        )
        self._update_tool_call_state(tool_call.id, ToolCallState.FINISHED)
        yield ToolResultEndEvent(
            reply_id=self.state.reply_id,
            tool_call_id=tool_call.id,
            state=state,
        )

    async def _convert_chat_response_to_event(
        self,
        block_ids: dict,
        chunk: Any,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Convert one ChatResponse chunk into agent events, keeping one
        open text stream and one open stream per pending tool call."""
        text_blocks = [
            block for block in chunk.content if isinstance(block, TextBlock)
        ]
        tool_call_blocks = [
            block for block in chunk.content if isinstance(block, ToolCallBlock)
        ]

        if text_blocks:
            if block_ids["text"] is None:
                block_ids["text"] = _generate_id()
                yield TextBlockStartEvent(
                    reply_id=self.state.reply_id,
                    block_id=block_ids["text"],
                )
            delta = "".join(block.text for block in text_blocks)
            # An empty delta must not add ghost text to the stream.
            if delta:
                yield TextBlockDeltaEvent(
                    reply_id=self.state.reply_id,
                    block_id=block_ids["text"],
                    delta=delta,
                )

        for tool_call in tool_call_blocks:
            if tool_call.id not in block_ids["tools"]:
                block_ids["tools"].append(tool_call.id)
                yield ToolCallStartEvent(
                    reply_id=self.state.reply_id,
                    tool_call_id=tool_call.id,
                    tool_call_name=tool_call.name,
                )
            if tool_call.input:
                yield ToolCallDeltaEvent(
                    reply_id=self.state.reply_id,
                    tool_call_id=tool_call.id,
                    delta=tool_call.input,
                )

    async def _acting(
        self,
        tool_calls: list[ToolCallBlock],
        skip_permission: bool = False,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute the tool calls of the current round in request order,
        saving one ToolResultBlock per call into the context and streaming
        the result lifecycle as events.

        With a permission engine, every call is checked first: ALLOW
        executes, DENY records a denied result without executing, and ASK
        parks the reply on a RequireUserConfirmEvent.
        """
        for tool_call in tool_calls:
            if not skip_permission and self.permission_engine is not None:
                tool = (
                    await self.toolkit.get_tool(tool_call.name)
                    if self.toolkit is not None
                    else None
                )
                if tool is not None:
                    decision = await self.permission_engine.check_permission(
                        tool,
                        self._parse_tool_input(tool_call),
                    )
                    if decision.behavior == PermissionBehavior.DENY:
                        async for evt in self._error_tool_result(
                            tool_call,
                            decision.message,
                            ToolResultState.DENIED,
                        ):
                            yield evt
                        continue
                    if decision.behavior == PermissionBehavior.ASK:
                        # **Note** the state update must happen before the
                        # event is yielded, mirroring the reference agent.
                        self._update_tool_call_state(
                            tool_call.id,
                            ToolCallState.ASKING,
                        )
                        yield RequireUserConfirmEvent(
                            reply_id=self.state.reply_id,
                            tool_calls=[tool_call],
                        )
                        return

            yield ToolResultStartEvent(
                reply_id=self.state.reply_id,
                tool_call_id=tool_call.id,
                tool_call_name=tool_call.name,
            )
            async for item in self.toolkit.call_tool(tool_call, self.state):
                if isinstance(item, ToolResponse):
                    for block in item.content:
                        if isinstance(block, TextBlock) and block.text:
                            yield ToolResultTextDeltaEvent(
                                reply_id=self.state.reply_id,
                                tool_call_id=tool_call.id,
                                delta=block.text,
                            )
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
                    yield ToolResultEndEvent(
                        reply_id=self.state.reply_id,
                        tool_call_id=tool_call.id,
                        state=item.state,
                        metadata=item.metadata,
                    )

    @staticmethod
    def _parse_tool_input(tool_call: ToolCallBlock) -> dict:
        """Best-effort parse of the tool call arguments for rule matching."""
        try:
            parsed = json.loads(tool_call.input)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _save_to_context(self, blocks: list, usage=None) -> None:
        msg_usage = None
        if usage is not None:
            msg_usage = Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_input_tokens=getattr(usage, "cache_input_tokens", 0) or 0,
                cache_creation_input_tokens=(
                    getattr(usage, "cache_creation_input_tokens", 0) or 0
                ),
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
