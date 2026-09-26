# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""The tool protocol in agentscope."""
import inspect
from abc import abstractmethod, ABC
from typing import AsyncGenerator, Any, Callable, List, TYPE_CHECKING

import jsonschema

from pydantic import BaseModel

from ..message import ToolResultState
from ._response import ToolChunk
from ._utils import _remove_title_field

if TYPE_CHECKING:
    from ..message import ToolResultBlock


class ParamsBase(BaseModel):
    """A base class for tool parameters that remove the title field from the
    exported JSON schema.
    """

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict:
        """An override implementation to remove the title field from the
        exported schema.
        """
        return _remove_title_field(super().model_json_schema(*args, **kwargs))


class ToolMiddlewareBase(ABC):
    """Base class for tool middlewares.

    A tool middleware wraps the execution of a tool in an onion fashion: the
    first registered middleware is the outermost layer and runs its pre-logic
    before any inner layer, then its post-logic after all inner layers have
    completed. Subclass this and implement :meth:`on_tool_call` — the signature
    is already spelled out, so second-party developers only need to fill in the
    body without reasoning about the wrapping protocol.

    Streaming and non-streaming tools are unified: ``next_handler`` always
    returns an async generator, so a middleware never needs to know whether the
    underlying tool yields a stream of chunks or returns a single chunk.

    Example:
        ```python
        class LoggingMiddleware(ToolMiddlewareBase):
            async def on_tool_call(self, tool, input_kwargs, next_handler):
                print(f"Calling {tool.name} with {input_kwargs}")
                async for chunk in next_handler(**input_kwargs):
                    yield chunk
                print(f"Finished {tool.name}")

        tool = MyTool(middlewares=[LoggingMiddleware()])
        ```
    """

    @abstractmethod
    async def on_tool_call(
        self,
        tool: "ToolBase",
        input_kwargs: dict[str, Any],
        next_handler: Callable[..., AsyncGenerator[ToolChunk, None]],
    ) -> AsyncGenerator[ToolChunk, None]:
        """Intercept a single tool invocation.

        Add pre-/post-logic around ``next_handler``, rewrite the tool inputs by
        passing modified keyword arguments to ``next_handler``, or transform
        the yielded chunks.

        Args:
            tool (`ToolBase`):
                The tool instance being invoked.
            input_kwargs (`dict[str, Any]`):
                The tool's input arguments for this invocation. Pass them on
                via ``next_handler(**input_kwargs)``; mutate or replace them to
                change what the inner layers and the tool itself receive.
            next_handler (`Callable[..., AsyncGenerator[ToolChunk, None]]`):
                Call it as ``next_handler(**input_kwargs)`` to run the next
                layer. It always returns an async generator, regardless of
                whether the underlying tool is streaming or not.

        Yields:
            `ToolChunk`:
                The chunks produced by this tool invocation.
        """


class ToolBase(ABC):
    """The tool protocol."""

    name: str
    """The name presented to the agent."""
    description: str
    """The agent-oriented tool description."""
    input_schema: dict[str, Any]
    """The input schema of the tool, following JSON schema format."""
    is_concurrency_safe: bool
    """If this tool is concurrency safe."""
    is_read_only: bool
    """If this tool is read-only, which will be used in the permission
    checking."""
    is_external_tool: bool = False
    """If this tool is an external tool, which doesn't need to implement the
    __call__ method and the agent will yield the external tool call event."""
    is_state_injected: bool = False
    """If this tool requires agent state to be injected when called. If `True`,
    the state will be injected by an argument named `_agent_state`. Note your
    tool should be able to accept such argument.
    """
    metadata_schema: dict[str, Any] | None = None
    """What an external executor must put in
    :attr:`~..message.ToolResultBlock.metadata`, as a JSON schema.

    The counterpart of :attr:`input_schema`: that one tells the model how
    to call the tool, this one tells whoever executes it how to answer.
    ``output`` stays whatever reads well to the model — this is the half
    a caller may depend on. ``None`` means nothing is promised."""

    is_mcp: bool = False
    """If this tool is an MCP tool, which will be used in the permission"""
    mcp_name: str | None = None
    """The name of the MCP server this tool belongs to, which is required if
    this tool is an MCP tool."""

    def __init__(
        self,
        middlewares: List["ToolMiddlewareBase"] | None = None,
    ) -> None:
        """Initialize the tool with optional middlewares.

        Args:
            middlewares (`List[ToolMiddlewareBase] | None`, optional):
                A list of :class:`ToolMiddlewareBase` instances wrapping the
                tool execution in an onion fashion. Defaults to an empty list.
        """
        self._middlewares: List["ToolMiddlewareBase"] = (
            middlewares if middlewares is not None else []
        )

    async def call(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ToolChunk | AsyncGenerator[ToolChunk, None]:
        """Execute the tool logic.

        This is the new override point for tool implementations.
        Subclasses should override this method instead of
        :meth:`__call__`.  The base implementation raises
        :exc:`NotImplementedError` for non-external tools and
        :exc:`RuntimeError` for external tools.

        Args:
            **kwargs: Tool input arguments.

        Returns:
            `ToolChunk | AsyncGenerator[ToolChunk, None]`:
                A single :class:`~agentscope.tool.ToolChunk` or an
                async generator that yields them.
        """
        if not self.is_external_tool:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not implement call",
            )

        raise RuntimeError(
            f"{self.__class__.__name__} is an external tool and should not "
            f"be called directly",
        )

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ToolChunk | AsyncGenerator[ToolChunk, None]:
        """Invoke the tool, layering any registered middlewares around
        :meth:`call`.

        Tools are always invoked with keyword arguments only. ``*args`` is
        accepted in the signature solely to stay Liskov-compatible with
        subclasses that override ``__call__`` with their own positional
        parameters; any positional argument actually passed here is rejected
        (raising :exc:`TypeError`) so it fails loudly instead of being silently
        dropped.

        Middlewares are applied in an onion fashion: the first registered
        middleware is the outermost layer and runs its pre-logic before
        any inner layers, then its post-logic after all inner layers
        have completed.
        """
        if args:
            raise TypeError(
                f"{type(self).__name__} must be called with keyword arguments "
                f"only, but got {len(args)} positional argument(s).",
            )
        # ``getattr`` with a default so the no-middleware path keeps working
        # even if a subclass overrides ``__init__`` without calling
        # ``super().__init__()``.
        middlewares = getattr(self, "_middlewares", [])
        if not middlewares:
            if inspect.isasyncgenfunction(self.call):
                return self.call(**kwargs)
            return await self.call(**kwargs)

        async def execute_chain(
            index: int = 0,
            **chain_kwargs: Any,
        ) -> AsyncGenerator[ToolChunk, None]:
            """Execute the tool middleware chain."""
            if index >= len(middlewares):
                # Innermost layer: run the tool's own ``call``. ``call`` is
                # always async but comes in two shapes — an async generator
                # function (e.g. ``Bash``) or a coroutine returning a single
                # ``ToolChunk`` / an async generator (e.g. ``FunctionTool``).
                # Normalize both into a single stream so middlewares never have
                # to distinguish them.
                if inspect.isasyncgenfunction(self.call):
                    async for chunk in self.call(**chain_kwargs):
                        yield chunk
                else:
                    result = await self.call(**chain_kwargs)
                    if isinstance(result, AsyncGenerator):
                        async for chunk in result:
                            yield chunk
                    else:
                        yield result
            else:
                mw = middlewares[index]
                input_kwargs = dict(chain_kwargs)

                async def next_handler(
                    **kw: Any,
                ) -> AsyncGenerator[ToolChunk, None]:
                    async for chunk in execute_chain(index + 1, **kw):
                        yield chunk

                async for chunk in mw.on_tool_call(
                    tool=self,
                    input_kwargs=input_kwargs,
                    next_handler=next_handler,
                ):
                    yield chunk

        return execute_chain(**kwargs)

    async def check_external_result(
        self,
        result: "ToolResultBlock",
    ) -> None:
        """Reject a result an external executor sent back.

        Called only for externally executed calls — a tool that produced
        its own result has nothing to check. Shape only, against
        :attr:`metadata_schema`; whether the content is any good is the
        caller's judgement, not this tool's, since a user who answers
        "no idea" has produced a perfectly valid result. Only successful
        results are checked, since the schema describes a successful run.

        Raises:
            `jsonschema.ValidationError`:
                If the metadata does not match what the tool promised its
                caller. The reply stays parked, so the executor can fix
                what it sent and try again.
        """
        if (
            self.metadata_schema is not None
            and result.state == ToolResultState.SUCCESS
        ):
            jsonschema.validate(result.metadata, self.metadata_schema)
