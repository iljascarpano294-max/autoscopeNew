"""Stage 7 task 1: middleware protocol and the onion executor."""

import asyncio

import pytest

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel
from agentscope.middleware import MiddlewareBase


def _text_response(text: str) -> ChatResponse:
    return ChatResponse(content=[TextBlock(text=text)], is_last=True)


class RecorderMiddleware(MiddlewareBase):
    """Wraps the raw model call, recording around it."""

    def __init__(self, label: str, log: list) -> None:
        self.label = label
        self.log = log

    async def on_model_call(self, agent, input_kwargs, next_handler):
        self.log.append(f"{self.label}-pre")
        result = await next_handler(**input_kwargs)
        self.log.append(f"{self.label}-post")
        return result


class DoubleCallMiddleware(MiddlewareBase):
    async def on_model_call(self, agent, input_kwargs, next_handler):
        await next_handler(**input_kwargs)
        return await next_handler(**input_kwargs)


class AppendPromptMiddleware(MiddlewareBase):
    def __init__(self, suffix: str) -> None:
        self.suffix = suffix

    async def on_system_prompt(self, agent, current_prompt: str) -> str:
        return current_prompt + self.suffix


def test_onion_order_is_enter_in_order_exit_in_reverse() -> None:
    log = []
    model = FakeChatModel([_text_response("hi")])
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        middlewares=[
            RecorderMiddleware("A", log),
            RecorderMiddleware("B", log),
        ],
    )

    reply = asyncio.run(agent.reply(UserMsg("Alice", "Hi")))

    assert reply.get_text_content() == "hi"
    assert log == ["A-pre", "B-pre", "B-post", "A-post"]
    # The model ran exactly once despite two middleware layers.
    assert len(model.calls) == 1


def test_unimplemented_hooks_are_skipped() -> None:
    # A middleware that overrides nothing behaves like no middleware.
    plain = Agent("Friday", "Prompt", FakeChatModel([_text_response("hi")]))
    with_noop = Agent(
        "Friday",
        "Prompt",
        FakeChatModel([_text_response("hi")]),
        middlewares=[MiddlewareBase()],
    )

    first = asyncio.run(plain.reply(UserMsg("Alice", "Hi")))
    second = asyncio.run(with_noop.reply(UserMsg("Alice", "Hi")))
    assert first.get_text_content() == second.get_text_content()


def test_double_next_handler_raises() -> None:
    model = FakeChatModel([_text_response("hi"), _text_response("hi again")])
    agent = Agent(
        "Friday",
        "Prompt",
        model,
        middlewares=[DoubleCallMiddleware()],
    )

    with pytest.raises(RuntimeError, match="only be consumed once"):
        asyncio.run(agent.reply(UserMsg("Alice", "Hi")))


def test_system_prompt_transformer_is_sequential() -> None:
    model = FakeChatModel([_text_response("hi")])
    agent = Agent(
        "Friday",
        "base",
        model,
        middlewares=[AppendPromptMiddleware("+A"), AppendPromptMiddleware("+B")],
    )

    asyncio.run(agent.reply(UserMsg("Alice", "Hi")))

    sent_system = model.calls[0][0][0]
    assert sent_system.get_text_content() == "base+A+B"


def test_input_rewrite_does_not_pollute_original_messages() -> None:
    class ReplaceMessages(MiddlewareBase):
        async def on_model_call(self, agent, input_kwargs, next_handler):
            # Replace the messages list entirely; the originals must not change.
            input_kwargs["messages"] = [input_kwargs["messages"][0]]
            return await next_handler(**input_kwargs)

    model = FakeChatModel([_text_response("hi")])
    agent = Agent("Friday", "Prompt", model, middlewares=[ReplaceMessages()])
    user_msg = UserMsg("Alice", "Hi")
    asyncio.run(agent.reply(user_msg))

    # The context still holds the original user message untouched.
    assert agent.state.context[0] is user_msg
    assert agent.state.context[0].get_text_content() == "Hi"
