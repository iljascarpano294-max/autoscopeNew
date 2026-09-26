"""Stage 5 task 2: streaming contract of the chat model."""

import asyncio

from agentscope.message import TextBlock, UserMsg
from agentscope.model import ChatResponse, FakeChatModel


def _stream_chunks(text_segments: list[str]) -> list[ChatResponse]:
    """Mirror the provider contract: delta chunks with is_last=False and a
    final chunk carrying the full text with is_last=True."""
    chunks = [
        ChatResponse(
            content=[TextBlock(text=segment, id="delta-block")],
            is_last=False,
        )
        for segment in text_segments
    ]
    chunks.append(
        ChatResponse(
            content=[TextBlock(text="".join(text_segments), id="delta-block")],
            is_last=True,
        ),
    )
    return chunks


def _user() -> list:
    return [UserMsg("Alice", "Hi")]


def test_fake_stream_contract() -> None:
    async def run():
        model = FakeChatModel(
            [
                _stream_chunks(["Hello, ", "streaming ", "world!"]),
                ChatResponse(
                    content=[TextBlock(text="second turn")],
                    is_last=True,
                ),
            ],
        )
        first_turn = [chunk async for chunk in await model(_user())]
        second_turn = await model(_user())
        return model, first_turn, second_turn

    model, first_turn, second_turn = asyncio.run(run())

    # The deltas pass through in order; only the final chunk is_last.
    texts = [chunk.content[0].text for chunk in first_turn]
    assert texts == [
        "Hello, ",
        "streaming ",
        "world!",
        "Hello, streaming world!",
    ]
    assert [chunk.is_last for chunk in first_turn] == [False, False, False, True]

    # One recorded model call per turn, even though the stream had 4 chunks.
    assert len(model.calls) == 2

    # The non-stream second turn still works after a streamed one.
    assert second_turn.content[0].text == "second turn"


def test_stream_single_response_passthrough() -> None:
    async def run():
        model = FakeChatModel(
            [[ChatResponse(content=[TextBlock(text="one shot")], is_last=True)]],
        )
        return [chunk async for chunk in await model(_user())]

    chunks = asyncio.run(run())
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert chunks[0].content[0].text == "one shot"


def test_stream_accumulates_when_no_final_chunk() -> None:
    async def run():
        model = FakeChatModel(
            [
                [
                    ChatResponse(
                        content=[TextBlock(text="a", id="b1")],
                        is_last=False,
                    ),
                    ChatResponse(
                        content=[TextBlock(text="b", id="b1")],
                        is_last=False,
                    ),
                    ChatResponse(
                        content=[TextBlock(text="c", id="b2")],
                        is_last=False,
                    ),
                ],
            ],
        )
        return [chunk async for chunk in await model(_user())]

    chunks = asyncio.run(run())
    # The provider stream ended without an is_last chunk, so the wrapper
    # yields the accumulated response to close the stream. Same-id deltas
    # merge into one block; a different id stays a separate block.
    assert [chunk.is_last for chunk in chunks] == [False, False, False, True]
    texts = [block.text for block in chunks[-1].content]
    assert texts == ["ab", "c"]


def test_stream_cancel_stops_consuming_responses() -> None:
    async def run():
        stream_config = _stream_chunks(["a", "b", "c", "d", "e", "f"])
        next_turn = ChatResponse(
            content=[TextBlock(text="next turn")],
            is_last=True,
        )
        model = FakeChatModel([stream_config, next_turn])
        received = []
        agen = await model(_user())
        async for chunk in agen:
            received.append(chunk)
            if len(received) == 2:
                break
        await agen.aclose()
        return stream_config, next_turn, model, received

    stream_config, next_turn, model, received = asyncio.run(run())

    # Only the first two delta chunks were pulled from the fake stream; the
    # remaining segments and the next turn's response are untouched.
    assert len(received) == 2
    assert stream_config[2].content[0].text == "c"
    assert model.responses == [next_turn]
    assert len(model.calls) == 1
