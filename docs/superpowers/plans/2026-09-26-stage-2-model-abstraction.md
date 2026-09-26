# Stage 2 Model Abstraction Implementation Plan

> For agentic workers: this plan is executed natively in the current task. The user asked for one plan and one branch per stage; do not dispatch other agents.

**Goal:** Run the stage 1 message types through a common chat model interface, a deterministic Fake model, and one OpenAI Chat Completions adapter.

**Architecture:** `ChatModelBase` owns retry and cancellation behavior; subclasses implement `_call_api`. A formatter maps `Msg` to provider messages. The OpenAI adapter maps provider text and tool calls back to `ChatResponse`; live credentials are optional for tests.

**Tech Stack:** Python 3.11, Pydantic 2, openai SDK, httpx MockTransport, pytest.

**Spec:** `PLAN.md` stage 2; `BASELINE.md` pins the reference implementation.

## Global Constraints

- Preserve `agentscope.model` and `agentscope.credential` public names needed for this slice.
- Do not require a real API key or network in automated tests.
- Keep provider tool calls as data; tool execution belongs to stage 4.
- Defer streaming, structured output, model cards, and vendor-specific parameters; describe these boundaries in the README.

## Review Focus

- A retriable failure must not silently consume a response or retry forever.
- Non-retriable errors must be raised without retry.
- Cancelling the model call must return an interrupted response.
- The formatter must not put tool-call blocks into a user message.
- The provider adapter must preserve both text and tool call ID/name/arguments.

---

### Task 1: Model base and deterministic Fake model

**Files:** Create `src/agentscope/model/_base.py`, `src/agentscope/model/_fake.py`; modify `src/agentscope/model/__init__.py`; test `tests/test_model_base.py`.

**Interfaces:** `ChatModelBase.__call__(messages, tools=None, tool_choice=None) -> ChatResponse`; subclass `_call_api(model_name, messages, tools, tool_choice)`; `FakeChatModel(responses)` consumes one queued response per call.

- [x] Write tests for text/tool responses, recorded input, retry budget, immediate failure, and cancellation.
- [x] Run `python -m pytest -q tests/test_model_base.py` and confirm expected failures.
- [x] Implement the base wrapper and Fake model.
- [x] Run `python -m pytest -q tests/test_model_base.py` and confirm all tests pass.

### Task 2: One real provider adapter with mock transport

**Files:** Create `src/agentscope/credential/_openai.py`, `src/agentscope/credential/__init__.py`, `src/agentscope/formatter/_openai.py`, `src/agentscope/formatter/__init__.py`, `src/agentscope/model/_openai_chat/_model.py`, `src/agentscope/model/_openai_chat/__init__.py`; modify `src/agentscope/model/__init__.py`, `pyproject.toml`; test `tests/test_openai_adapter.py`.

**Interfaces:** `OpenAICredential(api_key, base_url=None)`; `OpenAIChatFormatter.format(messages)`; `OpenAIChatModel(credential, model, ..., client_kwargs=None)`.

- [x] Write a no-network test with `httpx.MockTransport` asserting request body and text/tool response mapping.
- [x] Run `python -m pytest -q tests/test_openai_adapter.py` and confirm expected failures.
- [x] Implement credential, formatter, and adapter using `AsyncOpenAI.chat.completions.create`.
- [x] Run `python -m pytest -q tests/test_openai_adapter.py` and confirm all tests pass.

### Task 3: Example and full regression

**Files:** Create `examples/model_demo.py`; modify `README.md`, `PLAN.md`.

**Interfaces:** Example runs Fake model only and displays a model response; it requires no API key.

- [x] Add example and record the adapter's tested and deferred behavior.
- [x] Run `python examples/model_demo.py` and `python -m pytest -q tests`; confirm both pass.
- [x] Commit and push `codex/stage-2-model-abstraction`.
