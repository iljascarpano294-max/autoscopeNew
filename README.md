# AgentScope 渐进式重建

这是一个用于学习的 AgentScope 2.0 重建项目。参考仓库与固定提交见 [BASELINE.md](BASELINE.md)，阶段路线见 [PLAN.md](PLAN.md)。阶段 6 已接入权限引擎（ALLOW/DENY/ASK 三种决策）、确认停靠-恢复与中断清理；版本标记仍为 `0.0.0`，表示尚未完成参考项目的功能。

## 运行阶段 0

使用已经建立的 Conda 环境，在本目录执行：

```powershell
.\.conda\python.exe -m pip install -e . --no-deps
.\.conda\python.exe examples\smoke_import.py
.\.conda\python.exe -m pytest -q tests
.\.conda\python.exe -m pip check
```

示例应打印 `D:\code\agentscopeNew\src\agentscope\__init__.py`，以确认没有意外导入参考仓库。独立环境和完整依赖清单见 [ENVIRONMENT.md](ENVIRONMENT.md)。

## 阶段 1：消息与响应

运行 `python examples/message_demo.py` 可查看 `UserMsg`、助手的工具调用块和 `ChatResponse` 的数据形态。`Msg` 持有角色、内容块、ID 和元数据；`ChatResponse` 持有模型返回的内容及结束标记。对应测试为 `tests/test_message.py` 与 `tests/test_model_response.py`。

这一步只存储工具调用的数据，不执行工具。参考实现中的事件应用、权限规则和流式音频块将在后续阶段补齐。

## 阶段 2：模型抽象

运行 `python examples/model_demo.py` 可用 Fake 模型生成文本和工具调用数据。`ChatModelBase` 负责有限重试和取消处理，具体模型负责 `_call_api`。OpenAI 适配器已用 `httpx.MockTransport` 验证消息格式和文本/工具调用映射，不需要真实 API Key 或网络。

此阶段仅实现非流式 Chat Completions 路径。流式输出、结构化输出、模型卡片以及其他模型厂商将在后续阶段扩展。

## 阶段 3：最小 Agent

运行 `python examples/agent_demo.py` 可看到两轮离线对话。每次 `reply` 把新输入加入 `AgentState.context`，临时构造系统消息并附上历史，再调用模型；返回的 `ChatResponse` 转成 `AssistantMsg` 保存到上下文。系统消息不存入对话历史。

## 阶段 4：工具调用闭环

运行 `python examples/tool_demo.py` 可看到一次离线工具调用。调用链：`Agent.reply` 每轮先 `_reasoning`（把 `Toolkit.get_tool_schemas()` 的 schema 交给模型），模型返回 `ToolCallBlock` 后 `_acting` 调 `Toolkit.call_tool`：按 `input_schema` 用 json_repair 修复并显式 jsonschema 校验参数（未知工具、非法 JSON、缺必填参数、工具异常都变成带 `ToolResultState.ERROR` 的结果，不中断会话），执行工具并把流式 `ToolChunk` 累积成 `ToolResponse`；Agent 把它转成 `ToolResultBlock`，与工具调用块一起按 `reply_id` 并入同一条助手消息，再带着结果调模型，直到模型给出纯文本或达到 `max_iters`（`finished_reason="exceed_max_iters"`）。

与参考实现（提交 `5ff52f8`）的差异：Toolkit 只保留 basic 组的注册、schema 导出与调度，工具组/MCP/skill/内建工具留待阶段 8；`ToolBase` 裁剪了 permission 相关方法与危险路径检查（阶段 6）；`call_tool` 在 json_repair 之外增加显式 jsonschema 校验。测试为 `tests/test_tool.py`、`tests/test_toolkit.py`、`tests/test_agent_tool_loop.py`、`tests/test_tool_demo.py`。

## 阶段 5：事件与流式输出

运行 `python examples/stream_demo.py` 可在终端看到一次流式工具调用与增量文本。调用链：`Agent.reply_stream` 先发 `ReplyStartEvent`，每轮发 `ModelCallStartEvent`；`ChatModelBase.__call__` 返回分片异步生成器（delta 透传、空"载体"分片吸收、无收尾分片时用 `_StreamAccumulator` 聚合、取消时以 INTERRUPTED 收尾），Agent 把分片转成 `TextBlockStart/Delta/End` 与 `ToolCallStart/Delta/End` 事件，收尾的 is_last 分片（含完整内容）每轮只落一次上下文；工具结果以 `ToolResultStart/TextDelta/End` 事件流出；最后 `ModelCallEndEvent`、`ReplyEndEvent` 与唯一的最终 `Msg`。`reply()` 复用同一条流只取最终消息。`console.print_stream` 只消费事件渲染，不读 Agent 状态。

与参考实现的差异：事件模块只迁入 Reply/ModelCall/TextBlock/ToolCall/ToolResult 五类（Data/Thinking/Hint/确认/中断类随阶段 6/15 引入）；`ReplyStartEvent` 暂无 `session_id`（阶段 10 引入会话）；计划中的独立 `stream()` 方法与参考的 `stream: bool` 属性冲突，保持参考的 `__call__` 双形态入口；console 为纯文本渲染（参考的 rich 交互渲染器随 Web UI 阶段迁入）；`event_to_message` 按计划实现为严格状态机（参考 `Msg.append_event` 对坏事件是警告跳过）。测试为 `tests/test_event.py`、`tests/test_model_stream.py`、`tests/test_agent_stream.py`、`tests/test_console_stream.py`、`tests/test_stream_demo.py`。

## 阶段 6：状态、权限与中断

运行 `python examples/permission_demo.py` 可离线看到 ALLOW、DENY、ASK-确认、中断四条路径。调用链：`Agent._acting` 在执行每个工具调用前把解析后的参数交给 `PermissionEngine.check_permission`（判定顺序：deny 规则 → ask 规则 → 只读快路径 → 工具自身 `check_permissions` → allow 规则 → 模式兜底，五种模式各有独立方法）；ALLOW 直接执行；DENY 记一条 `ToolResultState.DENIED` 结果且不执行工具；ASK 把工具调用置为 ASKING 并在 `RequireUserConfirmEvent` 处停靠（流在此结束，无 ReplyEnd）。恢复时向 `reply_stream` 传入 `UserConfirmResultEvent`：ID 不在等待集合即抛错（重复提交/错误 ID 均不执行），确认只执行一次，拒绝转为 DENIED 结果；`UserInterruptEvent` 把所有待定调用闭合为 INTERRUPTED 并以 `finished_reason="interrupted"` 结束。停靠/中断状态都在 `AgentState.context` 里，`model_dump_json()/model_validate_json()` 可直接往返。

与参考实现的差异：`PermissionEngine` 与权限数据模型逐字迁入（危险路径辅助 `_is_dangerous_path`、工作目录检查随阶段 8 的文件工具引入）；恢复时沿用停靠回复的 reply_id（参考会为新 reply 生成新 ID），使结果并入同一条助手消息；外部执行事件（RequireExternalExecutionEvent）留到阶段 8/15。测试为 `tests/test_permission.py`、`tests/test_permission_engine.py`、`tests/test_agent_confirmation.py`、`tests/test_agent_interrupt.py`。
