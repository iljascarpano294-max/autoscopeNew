# Stage 3 Minimal Agent Implementation Plan

> For agentic workers: this plan is executed natively in the current task. The user asked for one plan and one branch per stage; do not dispatch other agents.

**Goal:** Provide a multi-turn `Agent` that accepts messages, sends system prompt plus conversation context to a model, and returns a completed assistant message.

**Architecture:** `AgentState` owns the conversation context. `Agent.reply` stores new inputs, calls `ChatModelBase`, converts the `ChatResponse` into `AssistantMsg`, then stores and returns it. Stage 4 will add the reasoning/action loop and tools; this stage rejects tool-call responses explicitly.

**Tech Stack:** Python 3.11, Pydantic 2, stage 1 messages, stage 2 model abstraction, pytest.

**Spec:** `PLAN.md` stage 3; `BASELINE.md` pins the reference implementation.

## Global Constraints

- Keep reference public names `agentscope.agent.Agent`, `Agent.reply`, `Agent.observe`, and `Agent.state.context`.
- Do not copy the reference `_agent.py` wholesale: its event, tool, permission, and middleware dependencies belong to later stages.
- Use Fake model in tests and examples; no API key, Redis, or network.
- Retain only user/assistant conversation messages in context; construct a system message for every model call.

## Review Focus

- Second turn must receive the first turn's user and assistant messages in order.
- Two Agent instances must not share conversation state.
- `observe` should store messages without invoking the model.
- A tool-call response must fail clearly without claiming the tool ran.
- A model error must not append a fabricated assistant response.

---

### Task 1: Isolated conversation state

**Files:** Create `src/agentscope/state/_state.py`, `src/agentscope/state/__init__.py`; test `tests/test_agent.py`.

**Interfaces:** `AgentState(context: list[Msg] = [])`, with an independent list per instance.

- [x] Write tests for independent state and injection into an Agent.
- [x] Run `python -m pytest -q tests/test_agent.py` and confirm expected failures.
- [x] Implement `AgentState` with a Pydantic default factory.
- [x] Run the state tests and confirm they pass.

### Task 2: Multi-turn reply and observation

**Files:** Create `src/agentscope/agent/_agent.py`, `src/agentscope/agent/__init__.py`; extend `tests/test_agent.py`.

**Interfaces:** `Agent(name, system_prompt, model, state=None)`; `await reply(inputs: Msg | list[Msg] | None) -> Msg`; `await observe(msgs: Msg | list[Msg] | None) -> None`.

- [x] Write tests for ordered model input, multi-turn context, `observe`, tool-call rejection, and model failure.
- [x] Run the tests and confirm expected failures.
- [x] Implement the smallest non-streaming reply path, mapping `ChatUsage` to message `Usage`.
- [x] Run `python -m pytest -q tests/test_agent.py` and confirm all tests pass.

### Task 3: Example and cumulative verification

**Files:** Create `examples/agent_demo.py`; modify `README.md`, `PLAN.md`.

**Interfaces:** Two offline conversation turns using `FakeChatModel`.

- [x] Add example and document the call path and deferred event/tool behavior.
- [x] Run `python examples/agent_demo.py`, `python -m pytest -q tests`, and `python -m pip check`; confirm all pass.
- [x] Commit and push `codex/stage-3-minimal-agent`.
