"""Stage 1 model response containers."""

from agentscope.message import TextBlock
from agentscope.model import ChatResponse, ChatUsage, FinishedReason


def test_response_mapping_and_usage() -> None:
    usage = ChatUsage(input_tokens=4, output_tokens=2, time=0.1)
    response = ChatResponse(content=[TextBlock(text="Hi")], is_last=True, usage=usage)
    assert dict(response)["is_last"] is True
    assert response.content[0].text == "Hi"
    assert response.usage.output_tokens == 2
    assert response.finished_reason == FinishedReason.COMPLETED


def test_append_text_by_block_id() -> None:
    response = ChatResponse(content=[], is_last=False)
    response.append_text("Hello", block_id="text-1")
    response.append_text(" world", block_id="text-1")
    response.append_text("!", block_id="text-2")
    assert [block.text for block in response.content] == ["Hello world", "!"]


def test_response_defaults_are_independent() -> None:
    first = ChatResponse(content=[], is_last=False)
    second = ChatResponse(content=[], is_last=True)
    first.metadata["marker"] = True
    first.content.append(TextBlock(text="one"))
    assert second.metadata == {}
    assert second.content == []
