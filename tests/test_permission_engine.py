"""Stage 6 task 2: PermissionEngine rule evaluation."""

import asyncio

from agentscope.message import TextBlock
from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionEngine,
    PermissionMode,
    PermissionRule,
)
from agentscope.tool import ToolBase, ToolChunk


class ReadOnlyTool(ToolBase):
    name = "read_thing"
    description = "Read only."
    input_schema = {"type": "object", "properties": {}}
    is_concurrency_safe = True
    is_read_only = True

    async def check_permissions(self, tool_input, context):
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="read-only tool defers to the engine",
        )

    async def call(self) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text="data")])


class WriteTool(ToolBase):
    name = "write_thing"
    description = "Writes."
    input_schema = {"type": "object", "properties": {}}
    is_concurrency_safe = False
    is_read_only = False

    async def check_permissions(self, tool_input, context):
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="write tool defers to the engine",
        )

    async def call(self) -> ToolChunk:
        return ToolChunk(content=[TextBlock(text="written")])


class AutoAllowTool(WriteTool):
    name = "auto_allow"

    async def check_permissions(self, tool_input, context):
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="tool allows itself",
        )


def _decide(engine: PermissionEngine, tool: ToolBase):
    return asyncio.run(engine.check_permission(tool, {}))


def test_deny_beats_allow() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    engine.add_rule(
        PermissionRule(
            tool_name="write_thing",
            rule_content=None,
            behavior=PermissionBehavior.ALLOW,
            source="userSettings",
        ),
    )
    engine.add_rule(
        PermissionRule(
            tool_name="write_thing",
            rule_content=None,
            behavior=PermissionBehavior.DENY,
            source="userSettings",
        ),
    )
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.DENY


def test_read_only_tool_is_allowed_by_mode() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    decision = _decide(engine, ReadOnlyTool())
    assert decision.behavior == PermissionBehavior.ALLOW

    explore = PermissionEngine(PermissionContext(mode=PermissionMode.EXPLORE))
    decision = _decide(explore, ReadOnlyTool())
    assert decision.behavior == PermissionBehavior.ALLOW


def test_no_rule_write_tool_asks_in_default_mode() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.ASK


def test_explore_mode_denies_write_tool() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.EXPLORE))
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.DENY


def test_allow_rule_allows_write_in_default_mode() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    engine.add_rule(
        PermissionRule(
            tool_name="write_thing",
            rule_content=None,
            behavior=PermissionBehavior.ALLOW,
            source="userSettings",
        ),
    )
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.ALLOW


def test_tool_check_permissions_allow_is_honored() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DEFAULT))
    decision = _decide(engine, AutoAllowTool())
    assert decision.behavior == PermissionBehavior.ALLOW


def test_dont_ask_mode_never_asks() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.DONT_ASK))
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.DENY
    assert decision.behavior != PermissionBehavior.ASK


def test_bypass_mode_allows_write_tool() -> None:
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.BYPASS))
    decision = _decide(engine, WriteTool())
    assert decision.behavior == PermissionBehavior.ALLOW
