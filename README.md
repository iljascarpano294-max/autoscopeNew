# AgentScope 渐进式重建

这是一个用于学习的 AgentScope 2.0 重建项目。参考仓库与固定提交见 [BASELINE.md](BASELINE.md)，阶段路线见 [PLAN.md](PLAN.md)。阶段 9 已实现多 Agent 编排（PipelineProtocol、SOPEngine 顺序流程与恢复、GoalPipeline 目标流水线）；版本标记仍为 `0.0.0`，表示尚未完成参考项目的功能。

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

## 阶段 7：中间件与上下文

运行 `python examples/middleware_demo.py` 可看到钩子触发顺序与预算行为。调用链：`Agent` 接受 `middlewares` 列表；`on_reply` 包裹整个 reply 流，每轮 `on_reasoning` 包裹推理阶段（`_reasoning_impl` 以 ChatResponse 作为末项标记交回循环），其中 `on_model_call` 包裹原始模型调用；`on_check_permission` 包裹权限判定、`on_acting` 包裹原始 `toolkit.call_tool`（`_acting_impl` 不写上下文）；`on_system_prompt` 按注册顺序变换系统提示。洋葱执行器保证注册顺序进入、逆序退出，同层 `next_handler` 重复消费抛错；未覆写的钩子自动跳过，无中间件时行为与阶段 6 完全一致。`BudgetMiddleware(max_model_calls)` 把计数存进 `agent.state.middle_context`（按 reply_id 键控，ReplyEnd 清理），超额直接抛错不再请求模型；`ContextCompressionMiddleware(max_messages, keep_recent, summarize)` 在回复开始前把旧消息折叠为一条摘要消息，旧摘要文本原样并入、每批消息只压缩一次。

与参考实现的差异：`MiddlewareBase` 逐字迁入；参考的 `ReplyBudgetControlMiddleware` 是 token 加权预算，本章按计划实现调用次数版 `BudgetMiddleware`，token 版随可观测性阶段再迁；压缩为计划指定的条数阈值+注入摘要函数（参考为 token 阈值+压缩工具+offloader），RAG/长期记忆/tracing 中间件分别留到阶段 13/16。测试为 `tests/test_middleware.py`、`tests/test_budget.py`、`tests/test_context_compression.py`、`tests/test_middleware_demo.py`。

## 阶段 8：工作空间、MCP 与 Skill

运行 `python examples/workspace_demo.py` 可看到工作空间内的写/读/搜索/命令执行与一次被拒绝的逃逸。调用链：`LocalWorkspace.resolve_path` 先 `Path.resolve()` 再用 `is_relative_to` 校验根目录归属，`..`、根外绝对路径与指向根外的符号链接统一抛 `WorkspaceError`；内建 Read/Write/Edit/Glob/Grep/Bash 全部经 `WorkspaceTool` 基类走该边界，Bash 以工作区为 cwd、带硬超时与输出截断。MCP 侧：`MCPClient`（StdioMCPConfig）显式 connect/list_tools/call_tool/close，`MCPTool` 适配器保留参考的命名清洗（`mcp__<server>__<tool>`）与内容转换，`Toolkit.add_mcp` 把 MCP 工具并入统一调度；连接关闭后再调用得到结构化 ERROR。Skill 侧：`LocalSkillLoader.load()` 扫描含 SKILL.md（YAML frontmatter）的子目录，缺 name/description 或目录逃逸（符号链接）抛 `SkillError`；Skill 只作为提示材料，不直接执行。

与参考实现的差异：参考的 `WorkspaceBase`（1581 行）是 Backend/沙箱/技能分区/MCP 网关的编排层，本章按计划实现最小本地切片并复用其 realpath+归属校验的安全语义；参考 `LocalWorkspace` 的技能分区与哈希校验随远程沙箱阶段迁入；MCP 仅本地 stdio（远程 HTTP/重连/网关后置）；Skill 内容暂未接入 Toolkit 提示（阶段 10 会话/服务时接入）。测试为 `tests/test_workspace_local.py`、`tests/test_builtin_workspace_tools.py`、`tests/test_mcp_local.py`、`tests/test_skill_local.py`。

## 阶段 9：多 Agent 编排

运行 `python examples/team_demo.py` 可看到两个 Agent 按目标协作与一次可追踪的成员失败。调用链：`PipelineProtocol` 是结构化协议（`reply_stream` 返回事件流），`Agent` 天然满足；`SOPEngine(sop, state)` 按 SOP 步骤顺序驱动各成员——第一步拿运行输入，后续步骤拿上一提交的 `<handover>` 文本块（重试附带上次拒绝反馈）；成员在工具确认处停靠时状态记 AWAITING 并结束流，恢复事件只路由到停靠步骤；验证器注入（SOPStep 的 verify 回调）出具判定，`max_attempts` 耗尽置 FAILED 且后续步骤不执行；`GoalPipeline` 把目标交给首个成员、依次交接结果，成员异常转为 MEMBER_FAILED 事件。所有步骤状态在 `SOPRunState` 中可 JSON 往返。

与参考实现的差异：SOP 状态机与引擎逐字迁入；参考 `SOPStep` 内建的模型自验证（brief/question 提示）简化为注入的 verify 回调（真实验证模型随阶段 10 服务层接入）；步骤边界事件（CustomEvent SOP_STEP_STARTED/ENDED）暂未发；动态团队工具随阶段 10/11 的服务与存储接入。测试为 `tests/test_pipeline_protocol.py`、`tests/test_sop_state.py`、`tests/test_sop_engine.py`、`tests/test_goal_pipeline.py`。

## 阶段 10：应用服务与会话

运行 `python examples/app_demo.py` 可在本地经 ASGI 完成一轮会话并验证重启后会话消失。调用链：`create_app(agent_factory)` 组装 `SessionService`（进程内字典，agent_factory 每会话构建一个 Agent 实例）与 `ChatService`（每会话一把 asyncio.Lock，同会话并发请求按获取顺序串行、不同会话独立，委托既有 `Agent.reply`）；HTTP 层 POST/GET/DELETE `/sessions`、POST `/sessions/{id}/messages`，Pydantic schema 校验输入（空消息 422），`SessionNotFound` 统一映射 404，模型异常映射为不含堆栈与内部信息的 500 且不残留伪助手消息；lifespan 关闭时清空会话。

与参考实现的差异：参考 app 层是大规模模块（服务/路由/频道/存储/任务），本章按计划只取进程内会话 + HTTP 三条路由的最小切片；非流式回复（reply_stream 事件经 SSE 的流式 API 随频道阶段接入）；持久化留到阶段 11。测试为 `tests/test_session_service.py`、`tests/test_chat_service.py`、`tests/test_app_api.py`、`tests/test_app_demo.py`。

## 阶段 11：持久化与分布式存储

运行 `python examples/storage_demo.py` 可看到同一会话跨"进程重启"继续对话。调用链：`StorageBase` 抽象（save_session/load_session/append_message/close），`SQLiteStorage` 用 sessions+messages 两表按 seq 保序，全部写入走事务——失败不留半个记录；`SessionService` 注入 storage 后，`ChatService` 在一轮成功完成后才 save+append（异常半轮不落盘）；重启后 `sessions.load()` 经注入的 agent_factory 重建 Agent 并还原上下文（顺序不变）；schema_version 过新或消息损坏抛 `StorageError`。`MessageBusBase`（publish/subscribe/ack）的 `InMemoryMessageBus` 按 event_id 去重、未 ack 事件可 redeliver 重试、topic 隔离；`RedisStorage`/`RedisMessageBus` 经 `AGENTSCOPE_REDIS_URL` 环境变量启用，缺配置或服务不可达时抛出可重试的结构化错误。

与参考实现的差异：参考 storage 层含 SQL/Redis/S3 与消息总线全集，本章按计划实现 SQLite + 进程内总线 + Redis 可选适配器的最小切片；Redis 总线为轮询式（参考为阻塞 pub/sub）；S3 blob store 与分布式协调后置。测试为 `tests/test_storage_sqlite.py`、`tests/test_persisted_chat.py`、`tests/test_message_bus.py`、`tests/test_storage_adapters.py`。

## 阶段 12：频道接入与 Web UI

运行 `python examples/channel_demo.py` 可看到入站到出站的离线闭环。调用链：频道事件归一为 `ChannelEvent`，`ChannelRouter` 以 `channel_id:external_user_id` 定位会话（跨频道隔离），`ChannelGateway` 在进入 Agent 前按 `message_id` 幂等去重（重复 webhook 不触发第二次聊天）；出站失败记录 `OutboundMessage` 重试状态并支持 `retry_outbound`。`FeishuChannel` 在事件进入 Agent 前完成 HMAC-SHA256 验签与时间戳容差校验（防重放），出站映射为飞书消息结构。SSE 侧：`ChatService.stream` 与 `GET /sessions/{id}/events` 流式输出（每帧带事件 id，`message` 事件为最终回复），`GET /sessions/{id}/messages` 供断线后重取；`examples/web_ui/index.html` 为无构建依赖的最小浏览器页面。

与参考实现的差异：参考频道层含网关签名路由、多平台适配器与流式中转，本章按计划实现 Mock 闭环 + 飞书一个适配器（验签方案为简化 HMAC 契约，真实飞书 AES 加密回调以适配器替换），Discord/钉钉未覆盖；Web UI 为静态页面（参考的前端构建链未迁入）。测试为 `tests/test_channel_gateway.py`、`tests/test_channel_feishu.py`、`tests/test_web_stream.py`、`tests/test_channel_demo.py`。
