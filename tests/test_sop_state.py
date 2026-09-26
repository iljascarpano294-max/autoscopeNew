"""Stage 9 task 2: SOP schema and run state."""

import pytest

from agentscope.message import TextBlock, UserMsg
from agentscope.sop import SOP, SOPPhase, SOPRunState, SOPStepRunState


def _state_with_two_steps() -> SOPRunState:
    first = SOPStepRunState(phase=SOPPhase.COMPLETED)
    first.given = [UserMsg("Alice", "start")]
    first.submission = [TextBlock(text="the plan")]

    second = SOPStepRunState(phase=SOPPhase.AWAITING)
    return SOPRunState(steps=[first, second])


def test_sop_state_roundtrip() -> None:
    state = _state_with_two_steps()
    assert state.phase == SOPPhase.AWAITING

    restored = SOPRunState.model_validate_json(state.model_dump_json())

    # The phase and per-step records survive the round trip unchanged.
    assert restored.phase == SOPPhase.AWAITING
    assert [step.phase for step in restored.steps] == [
        SOPPhase.COMPLETED,
        SOPPhase.AWAITING,
    ]
    assert restored.steps[0].submission is not None
    assert restored.steps[0].submission[0].text == "the plan"
    assert restored.steps[0].given[0].get_text_content() == "start"


def test_run_phase_is_derived_from_steps() -> None:
    all_pending = SOPRunState(steps=[SOPStepRunState(), SOPStepRunState()])
    assert all_pending.phase == SOPPhase.PENDING

    completed = SOPRunState(
        steps=[
            SOPStepRunState(phase=SOPPhase.COMPLETED),
            SOPStepRunState(phase=SOPPhase.COMPLETED),
        ],
    )
    assert completed.phase == SOPPhase.COMPLETED

    failed = SOPRunState(
        steps=[
            SOPStepRunState(phase=SOPPhase.COMPLETED),
            SOPStepRunState(phase=SOPPhase.FAILED),
        ],
    )
    assert failed.phase == SOPPhase.FAILED

    running = SOPRunState(
        steps=[
            SOPStepRunState(phase=SOPPhase.COMPLETED),
            SOPStepRunState(phase=SOPPhase.RUNNING),
        ],
    )
    assert running.phase == SOPPhase.RUNNING


def test_sop_holds_steps() -> None:
    class Step:
        subject = "step one"

    sop = SOP(name="two-step", steps=[Step(), Step()])
    assert sop.name == "two-step"
    assert len(sop.steps) == 2
