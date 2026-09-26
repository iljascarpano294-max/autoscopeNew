# 兼容性矩阵（对照参考提交 5ff52f8）

状态含义：**已对齐** = 名称与行为和参考一致并有测试；**部分** = 核心语义一致但功能子集；**暂缓** = 参考存在、本项目尚未迁入。
`tests/test_public_api.py` 会解析本表并验证所有"已对齐"名称可导入。

| 模块 | 名称 | 状态 |
| --- | --- | --- |
| agentscope.message | Msg | 已对齐 |
| agentscope.message | UserMsg | 已对齐 |
| agentscope.message | AssistantMsg | 已对齐 |
| agentscope.message | SystemMsg | 已对齐 |
| agentscope.message | TextBlock | 已对齐 |
| agentscope.message | ToolCallBlock | 已对齐 |
| agentscope.message | ToolResultBlock | 已对齐 |
| agentscope.message | ToolResultState | 已对齐 |
| agentscope.message | DataBlock | 已对齐 |
| agentscope.message | Usage | 已对齐 |
| agentscope.model | ChatModelBase | 已对齐 |
| agentscope.model | ChatResponse | 已对齐 |
| agentscope.model | ChatUsage | 已对齐 |
| agentscope.model | FinishedReason | 已对齐 |
| agentscope.model | FakeChatModel | 已对齐 |
| agentscope.model | OpenAIChatModel | 已对齐 |
| agentscope.model | DeepSeekChatModel | 已对齐 |
| agentscope.model | AnthropicChatModel | 暂缓 |
| agentscope.model | GeminiChatModel | 暂缓 |
| agentscope.agent | Agent | 已对齐 |
| agentscope.agent | A2AAgent | 部分对齐 |
| agentscope.agent | RealtimeAgent | 部分对齐 |
| agentscope.tool | Toolkit | 已对齐 |
| agentscope.tool | ToolBase | 已对齐 |
| agentscope.tool | ToolChunk | 已对齐 |
| agentscope.tool | ToolResponse | 已对齐 |
| agentscope.tool | FunctionTool | 已对齐 |
| agentscope.tool | RegisteredTool | 已对齐 |
| agentscope.tool | ToolChoice | 已对齐 |
| agentscope.tool | Bash | 已对齐 |
| agentscope.tool | Edit | 已对齐 |
| agentscope.tool | Glob | 已对齐 |
| agentscope.tool | Grep | 已对齐 |
| agentscope.tool | Read | 已对齐 |
| agentscope.tool | Write | 已对齐 |
| agentscope.tool | MCPTool | 已对齐 |
| agentscope.state | AgentState | 已对齐 |
| agentscope.state | A2AState | 已对齐 |
| agentscope.permission | PermissionEngine | 已对齐 |
| agentscope.permission | PermissionContext | 已对齐 |
| agentscope.permission | PermissionDecision | 已对齐 |
| agentscope.permission | PermissionRule | 已对齐 |
| agentscope.permission | PermissionMode | 已对齐 |
| agentscope.permission | PermissionBehavior | 已对齐 |
| agentscope.event | EventType | 已对齐 |
| agentscope.event | ReplyStartEvent | 已对齐 |
| agentscope.event | ReplyEndEvent | 已对齐 |
| agentscope.event | ModelCallStartEvent | 已对齐 |
| agentscope.event | ModelCallEndEvent | 已对齐 |
| agentscope.event | TextBlockStartEvent | 已对齐 |
| agentscope.event | TextBlockDeltaEvent | 已对齐 |
| agentscope.event | TextBlockEndEvent | 已对齐 |
| agentscope.event | ToolCallStartEvent | 已对齐 |
| agentscope.event | ToolCallEndEvent | 已对齐 |
| agentscope.event | ToolResultStartEvent | 已对齐 |
| agentscope.event | ToolResultEndEvent | 已对齐 |
| agentscope.event | RequireUserConfirmEvent | 已对齐 |
| agentscope.event | UserConfirmResultEvent | 已对齐 |
| agentscope.event | UserInterruptEvent | 已对齐 |
| agentscope.event | CustomEvent | 已对齐 |
| agentscope.middleware | MiddlewareBase | 已对齐 |
| agentscope.middleware | BudgetMiddleware | 部分对齐 |
| agentscope.middleware | ContextCompressionMiddleware | 部分对齐 |
| agentscope.middleware | RAGMiddleware | 已对齐 |
| agentscope.middleware | TracingMiddleware | 部分对齐 |
| agentscope.pipeline | PipelineProtocol | 已对齐 |
| agentscope.pipeline | GoalPipeline | 部分对齐 |
| agentscope.sop | SOP | 已对齐 |
| agentscope.sop | SOPStep | 已对齐 |
| agentscope.sop | SOPEngine | 已对齐 |
| agentscope.sop | SOPPhase | 已对齐 |
| agentscope.sop | SOPRunState | 已对齐 |
| agentscope.workspace | LocalWorkspace | 已对齐 |
| agentscope.workspace | SandboxedWorkspace | 已对齐 |
| agentscope.workspace | DockerBackend | 已对齐 |
| agentscope.workspace | E2BBackend | 已对齐 |
| agentscope.mcp | MCPClient | 已对齐 |
| agentscope.mcp | MCPTool | 已对齐 |
| agentscope.mcp | StdioMCPConfig | 已对齐 |
| agentscope.skill | Skill | 已对齐 |
| agentscope.skill | LocalSkillLoader | 已对齐 |
| agentscope.rag | TextParser | 已对齐 |
| agentscope.rag | ApproxTokenChunker | 已对齐 |
| agentscope.rag | KnowledgeBase | 已对齐 |
| agentscope.rag | InMemoryVectorStore | 已对齐 |
| agentscope.app | create_app | 部分对齐 |
| agentscope.console | print_stream | 部分对齐 |
| agentscope.realtime | RealtimeAggregator | 部分对齐 |
| agentscope.realtime | InMemoryRealtimeTransport | 部分对齐 |
| agentscope.embedding | — | 暂缓 |
| agentscope.tts | — | 暂缓 |
| agentscope.hub | — | 暂缓 |
| agentscope.tui | — | 暂缓 |

## 暂缓清单（参考存在、本项目未覆盖）

- 模型适配器：Anthropic、Gemini、DashScope、Moonshot、Ollama、VolcEngine、xAI、OpenAI Responses API。
- 结构化输出（StructuredOutputError 及生成工具）、count_tokens。
- 频道：Discord、钉钉、真实飞书 AES 加密回调、channel 网关签名路由全集。
- 存储：SQLAlchemy 多后端、Redis 在线语义（阻塞 pub/sub）、S3 blob store、多进程协调。
- 工作空间：Daytona、K8s、AppleContainer、Bubblewrap、OpenSandbox 后端与 MCP 网关。
- 实时：OpenAI/Gemini/DashScope 实时模型、WebSocket 传输、TTS 中间件。
- A2A：官方 A2A SDK 全协议、agent 卡片协商。
- 前端：examples/web_ui 的参考构建链（Vite/React）。
- 可观测性：OpenTelemetry SDK 导出、预算 token 加权中间件。
- Hub/技能市场、TUI 终端界面。
