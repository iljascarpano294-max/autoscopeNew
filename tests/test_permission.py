"""Stage 6 task 1: permission data model."""

import pytest
from pydantic import ValidationError

from agentscope.permission import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionMode,
    PermissionRule,
)


def test_permission_modes_and_behaviors_serialize() -> None:
    assert PermissionMode.DEFAULT.value == "default"
    assert PermissionMode.ACCEPT_EDITS.value == "accept_edits"
    assert PermissionMode.EXPLORE.value == "explore"
    assert PermissionMode.BYPASS.value == "bypass"
    assert PermissionMode.DONT_ASK.value == "dont_ask"

    assert PermissionBehavior.ALLOW.value == "allow"
    assert PermissionBehavior.DENY.value == "deny"
    assert PermissionBehavior.ASK.value == "ask"
    assert PermissionBehavior.PASSTHROUGH.value == "passthrough"

    rule = PermissionRule(
        tool_name="add",
        rule_content=None,
        behavior=PermissionBehavior.ALLOW,
        source="userSettings",
    )
    dumped = rule.model_dump()
    assert dumped["tool_name"] == "add"
    assert dumped["behavior"] in (PermissionBehavior.ALLOW, "allow")


def test_rule_carries_tool_name_and_behavior() -> None:
    deny = PermissionRule(
        tool_name="bash",
        rule_content="rm:*",
        behavior=PermissionBehavior.DENY,
        source="projectSettings",
    )
    assert deny.tool_name == "bash"
    assert deny.behavior == PermissionBehavior.DENY
    assert deny.rule_content == "rm:*"


def test_rule_missing_tool_name_fails() -> None:
    with pytest.raises(ValidationError):
        PermissionRule(
            rule_content=None,
            behavior=PermissionBehavior.ALLOW,
            source="userSettings",
        )


def test_rule_invalid_behavior_fails() -> None:
    with pytest.raises(ValidationError):
        PermissionRule(
            tool_name="add",
            rule_content=None,
            behavior="sometimes",
            source="userSettings",
        )


def test_context_defaults_and_decision() -> None:
    context = PermissionContext()
    assert context.mode == PermissionMode.DEFAULT
    assert context.allow_rules == {}
    assert context.deny_rules == {}
    assert context.ask_rules == {}

    decision = PermissionDecision(
        behavior=PermissionBehavior.ASK,
        message="Confirm?",
    )
    assert decision.behavior == PermissionBehavior.ASK
    assert decision.bypass_immune is False
    assert decision.updated_input is None
    assert decision.suggested_rules is None
