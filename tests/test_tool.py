"""Stage 4 tool protocol: ToolChunk / ToolResponse shapes and conversion."""

import base64

from agentscope.message import (
    Base64Source,
    DataBlock,
    TextBlock,
    ToolResultBlock,
    ToolResultState,
)
from agentscope.tool import ToolChunk, ToolResponse


def test_tool_chunk_defaults() -> None:
    chunk = ToolChunk(content=[TextBlock(text="Hello, world!")])
    assert chunk.state == ToolResultState.RUNNING
    assert chunk.is_last is True
    assert chunk.metadata == {}
    assert chunk.id
    dumped = chunk.model_dump()
    assert dumped["content"][0]["text"] == "Hello, world!"
    assert dumped["state"] == "running"
    assert dumped["is_last"] is True


def test_tool_response_accumulates_text_chunks() -> None:
    response = ToolResponse(id="call-1")
    response.append_chunk(
        ToolChunk(content=[TextBlock(text="123", id="a")]),
    )
    response.append_chunk(
        ToolChunk(content=[TextBlock(text="456", id="a")]),
    )
    assert response.id == "call-1"
    assert response.state == ToolResultState.SUCCESS
    assert [block.text for block in response.content] == ["123456"]


def test_streaming_chunks_merge_consecutive_text() -> None:
    response = ToolResponse(id="call-2")
    for chunk in [
        ToolChunk(content=[TextBlock(text="123", id="a")]),
        ToolChunk(content=[TextBlock(text="456", id="b")]),
        ToolChunk(content=[TextBlock(text="789", id="b")]),
    ]:
        response.append_chunk(chunk)
    assert [block.text for block in response.content] == ["123456789"]


def test_tool_response_state_escalates_to_error() -> None:
    response = ToolResponse(id="call-1")
    response.append_chunk(ToolChunk(content=[TextBlock(text="partial")]))
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="boom")],
            state=ToolResultState.ERROR,
        ),
    )
    assert response.state == ToolResultState.ERROR
    assert [block.text for block in response.content] == ["partialboom"]


def test_tool_response_accumulates_metadata() -> None:
    response = ToolResponse(id="call-1")
    response.append_chunk(
        ToolChunk(content=[TextBlock(text="hi")], metadata={"n": 1}),
    )
    response.append_chunk(ToolChunk(content=[], metadata={"extra": True}))
    assert response.metadata == {"n": 1, "extra": True}


def test_base64_data_chunks_merge_by_bytes() -> None:
    response = ToolResponse(id="call-3")
    first = base64.b64encode(b"abc").decode("ascii")
    second = base64.b64encode(b"def").decode("ascii")
    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="1",
                    source=Base64Source(data=first, media_type="image/jpeg"),
                ),
            ],
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="1",
                    source=Base64Source(data=second, media_type="image/jpeg"),
                ),
            ],
        ),
    )
    merged = response.content[0]
    assert isinstance(merged, DataBlock)
    assert isinstance(merged.source, Base64Source)
    assert base64.b64decode(merged.source.data) == b"abcdef"


def test_tool_results_convert_to_blocks_with_call_id() -> None:
    """Success and failure results both convert into ToolResultBlock."""
    cases = [
        (ToolResultState.RUNNING, ToolResultState.SUCCESS),
        (ToolResultState.ERROR, ToolResultState.ERROR),
    ]
    for chunk_state, response_state in cases:
        chunk = ToolChunk(
            content=[TextBlock(text="payload")],
            state=chunk_state,
            metadata={"k": "v"},
        )
        response = ToolResponse(id="call-9").append_chunk(chunk)
        block = ToolResultBlock(
            id="call-9",
            name="add",
            output=response.content,
            state=response.state,
            metadata=response.metadata,
        )
        assert block.id == "call-9"
        assert block.name == "add"
        assert block.state == response_state
        assert block.output == response.content
        assert block.metadata == {"k": "v"}


def test_empty_results_do_not_share_mutable_state() -> None:
    first = ToolResponse(id="a")
    second = ToolResponse(id="b")
    assert first.content is not second.content
    assert first.metadata is not second.metadata

    chunk_a = ToolChunk(content=[])
    chunk_b = ToolChunk(content=[])
    assert chunk_a.content is not chunk_b.content
    assert chunk_a.metadata is not chunk_b.metadata

    first.append_chunk(ToolChunk(content=[TextBlock(text="x")]))
    assert second.content == []
