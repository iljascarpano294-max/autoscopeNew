# Stage 1 Message and Response Implementation Plan

> For agentic workers: this plan is executed natively in the current task. The user asked for one plan and one branch per stage; do not dispatch other agents.

**Goal:** Create serializable message blocks, role-specific messages, and model response containers without requiring a model API.

**Architecture:** Pydantic models represent message blocks and messages; dataclasses represent model responses and usage. Public imports mirror the reference package's `agentscope.message` and `agentscope.model` names for this stage.

**Tech Stack:** Python 3.11, Pydantic 2, pytest.

**Spec:** `PLAN.md` stage 1; reference commit and local exceptions are recorded in `BASELINE.md`.

## Global Constraints

- Use the `agentscope` package name and the independent `.conda` environment.
- Keep this stage runnable without API keys, external services, or model calls.
- Follow reference message roles and block type names; defer event application, permission decisions, and streaming execution to later stages.
- Add only imports used in this stage. Record intentionally deferred reference behavior in the README.

## Review Focus

- Reject tool-call blocks in user messages and non-text blocks in system messages.
- Preserve explicit IDs and metadata during serialization.
- Do not share mutable content defaults between messages or responses.
- A response's `is_last` flag must survive serialization.
- Text extraction must ignore non-text blocks.

---

### Task 1: Message blocks and role validation

**Files:** Create `src/agentscope/message/_block.py`, `src/agentscope/message/_base.py`, `src/agentscope/message/__init__.py`; test `tests/test_message.py`.

**Interfaces:** Produce `TextBlock`, `ThinkingBlock`, `ToolCallBlock`, `ToolResultBlock`, `DataBlock`, `Msg`, `UserMsg(name, content)`, `AssistantMsg(name, content)`, `SystemMsg(name, content)`, and `Msg.get_text_content()`.

- [x] Write tests for constructors, JSON serialization, explicit IDs, independent defaults, text extraction, and role validation.
- [x] Run `python -m pytest -q tests/test_message.py` and confirm expected failures.
- [x] Implement block models and message constructors using Pydantic discriminated block types and role validation.
- [x] Run `python -m pytest -q tests/test_message.py` and confirm all tests pass.

### Task 2: Model response and usage data

**Files:** Create `src/agentscope/model/_model_response.py`, `src/agentscope/model/_model_usage.py`, `src/agentscope/model/__init__.py`; test `tests/test_model_response.py`.

**Interfaces:** Produce `ChatResponse(content, is_last)`, `ChatUsage(input_tokens, output_tokens, time)`, `FinishedReason`, `StructuredResponse`; `ChatResponse.append_text(text, block_id=None)` follows reference accumulation behavior.

- [x] Write tests for response serialization, distinct default content, `is_last`, usage, and text accumulation by block ID.
- [x] Run `python -m pytest -q tests/test_model_response.py` and confirm expected failures.
- [x] Implement response containers without provider or tool imports.
- [x] Run `python -m pytest -q tests/test_model_response.py` and confirm all tests pass.

### Task 3: End-to-end data-shape example

**Files:** Create `examples/message_demo.py`; modify `README.md`, `PLAN.md`.

**Interfaces:** Demonstrate a user message, assistant text, and a tool-call block as data only.

- [x] Add example and document the data flow and deferred functionality.
- [x] Run `python examples/message_demo.py` and `python -m pytest -q tests`; confirm both pass.
- [x] Commit and push `codex/stage-1-message-response`.
