"""Stage 1 message shape and role rules."""

import pytest

from agentscope.message import (
    AssistantMsg,
    Msg,
    SystemMsg,
    TextBlock,
    ToolCallBlock,
    UserMsg,
)


def test_text_message_round_trip_and_explicit_id() -> None:
    msg = UserMsg("Alice", "Hello", id="user-1", metadata={"source": "test"})
    restored = Msg.model_validate_json(msg.model_dump_json())
    assert restored.id == "user-1"
    assert restored.role == "user"
    assert restored.metadata == {"source": "test"}
    assert restored.get_text_content() == "Hello"


def test_text_extraction_ignores_tool_calls() -> None:
    msg = AssistantMsg(
        "Friday",
        [TextBlock(text="I'll check"), ToolCallBlock(id="call-1", name="search", input="{}")],
    )
    assert msg.get_text_content() == "I'll check"
    assert msg.get_content_blocks("tool_call")[0].name == "search"


def test_roles_reject_invalid_blocks() -> None:
    tool = ToolCallBlock(id="call-1", name="search", input="{}")
    with pytest.raises(ValueError, match="User message"):
        UserMsg("Alice", [tool])
    with pytest.raises(ValueError, match="System message"):
        SystemMsg("system", [tool])


def test_mutable_defaults_are_independent() -> None:
    first = UserMsg("A", "one")
    second = UserMsg("B", "two")
    first.metadata["tag"] = 1
    first.content.append(TextBlock(text="extra"))
    assert second.metadata == {}
    assert second.get_text_content() == "two"
