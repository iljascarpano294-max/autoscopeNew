"""Stage 10 task 1: in-process session records and service."""

import pytest

from agentscope.agent import Agent
from agentscope.app._service import SessionNotFound, SessionService
from agentscope.message import UserMsg
from agentscope.model import FakeChatModel


def _agent() -> Agent:
    return Agent("Friday", "Prompt", FakeChatModel([]))


def test_session_lifecycle() -> None:
    service = SessionService(agent_factory=_agent)

    record = service.create(agent_id="demo-agent")
    assert record.session_id
    assert record.agent_id == "demo-agent"
    assert record.created_at

    # Reading returns the same record.
    assert service.get(record.session_id) is record

    # Two sessions never share state.
    other = service.create(agent_id="demo-agent")
    assert other.session_id != record.session_id
    other.agent.state.context.append(UserMsg("Alice", "mine"))
    assert record.agent.state.context == []

    # Deleting removes the record; a later get raises not-found.
    service.delete(record.session_id)
    with pytest.raises(SessionNotFound):
        service.get(record.session_id)

    # Deleting an unknown session is reported, not silent.
    with pytest.raises(SessionNotFound):
        service.delete(record.session_id)
