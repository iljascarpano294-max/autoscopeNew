"""Stage 16 task 2: structured logging, metrics and secret redaction."""

import asyncio

from agentscope.agent import Agent
from agentscope.message import TextBlock, UserMsg
from agentscope.middleware import TracingMiddleware
from agentscope.middleware._tracing import InMemoryExporter, setup_tracing
from agentscope.model import ChatResponse, FakeChatModel

SECRET = "sk-test-1234567890abcdef"


def test_log_redaction() -> None:
    from agentscope._logging import build_log_record

    record = build_log_record(
        run_id="run-1",
        session_id="session-1",
        event_type="tool.call",
        fields={"api_key": SECRET, "tool": "add", "duration_ms": 12},
        secrets=[SECRET],
    )

    dumped = str(record)
    assert SECRET not in dumped
    assert record["run_id"] == "run-1"
    assert record["session_id"] == "session-1"
    assert record["event_type"] == "tool.call"
    assert record["fields"]["api_key"] == "[REDACTED]"


def test_span_attributes_never_contain_tool_inputs() -> None:
    exporter = InMemoryExporter()
    setup_tracing(exporter=exporter)

    async def run():
        # The tool receives a secret-looking input; spans must not record it.
        from agentscope.message import ToolCallBlock
        from agentscope.tool import ToolBase, ToolChunk, Toolkit

        class SecretTool(ToolBase):
            name = "vault_read"
            description = "Reads with a credential."
            input_schema = {
                "type": "object",
                "properties": {"api_key": {"type": "string"}},
                "required": ["api_key"],
            }
            is_concurrency_safe = True
            is_read_only = True

            async def check_permissions(self, tool_input, context):
                from agentscope.permission import PermissionBehavior, PermissionDecision

                return PermissionDecision(behavior=PermissionBehavior.ALLOW, message="ok")

            async def call(self, api_key: str) -> ToolChunk:
                return ToolChunk(content=[TextBlock(text="vault contents")])

        model = FakeChatModel(
            [
                ChatResponse(
                    content=[
                        ToolCallBlock(
                            id="call-1",
                            name="vault_read",
                            input=f'{{"api_key": "{SECRET}"}}',
                        ),
                    ],
                    is_last=True,
                ),
                ChatResponse(content=[TextBlock(text="vault opened")], is_last=True),
            ],
        )
        agent = Agent(
            "Friday",
            "Prompt",
            model,
            toolkit=Toolkit(tools=[SecretTool()]),
            middlewares=[TracingMiddleware()],
        )
        await agent.reply(UserMsg("Alice", "read the vault"))

    asyncio.run(run())

    span_dump = "".join(
        str(span.__dict__) + str(span.attributes) for span in exporter.spans
    )
    assert SECRET not in span_dump


def test_metrics_count_calls_and_failures() -> None:
    from agentscope.middleware._tracing import get_metrics, setup_tracing

    metrics = setup_tracing(exporter=InMemoryExporter()).metrics
    metrics.reset()

    ok_agent = Agent(
        "Friday",
        "Prompt",
        FakeChatModel([ChatResponse(content=[TextBlock(text="ok")], is_last=True)]),
        middlewares=[TracingMiddleware()],
    )
    failing_agent = Agent(
        "Saturday",
        "Prompt",
        FakeChatModel([RuntimeError("model down")]),
        middlewares=[TracingMiddleware()],
    )

    asyncio.run(ok_agent.reply(UserMsg("Alice", "hi")))

    async def failing():
        async for _ in failing_agent.reply_stream(UserMsg("Alice", "hi")):
            pass

    import pytest

    with pytest.raises(RuntimeError):
        asyncio.run(failing())

    metrics = get_metrics()
    assert metrics.model_calls == 2
    assert metrics.model_failures == 1
    assert metrics.total_model_latency_ms >= 0
