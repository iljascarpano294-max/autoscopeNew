# AgentScope 从零重建学习计划

## 目标与边界

- 参考项目：`D:\code\agentscope`，当前检查到的提交为 `5ff52f8`。新项目：`D:\code\agentscopeNew`。
- 目标是通过分阶段重建理解 AgentScope 2.0，最终保持需要的公开接口和核心逻辑与参考项目一致；允许直接迁入原实现，不把“重新发明算法”当作学习任务。
- 每阶段先明确输入、输出和依赖，再迁入代码；完成一个可运行的纵向功能后才进入下一阶段。
- 参考仓库在开始时已有未提交改动。后续以固定提交为基准；确实要参考工作区改动时，单独记录文件与原因。

## 当前进度

- 阶段 0 已在 `codex/stage-0-skeleton` 分支完成。参考提交和工作区差异见 `BASELINE.md`；安装与验证命令见 `README.md` 和 `ENVIRONMENT.md`。
- 阶段 1 已在 `codex/stage-1-message-response` 分支完成消息与响应的数据结构和示例。
- 阶段 2 已在 `codex/stage-2-model-abstraction` 分支完成模型抽象、Fake 模型和一个适配器。
- 阶段 3 已在 `codex/stage-3-minimal-agent` 分支完成非流式多轮文本 Agent。
- 阶段 4 已在 `codex/stage-4-tool-loop` 分支完成工具调用闭环（ToolBase/ToolChunk/ToolResponse/Toolkit/FunctionTool + Agent 推理-行动循环）。
- 阶段 5 已在 `codex/stage-5-events-streaming` 分支完成事件与流式输出（事件模型与 event_to_message、模型流式契约、reply_stream 事件生产、console.print_stream）。
- 阶段 6 已在 `codex/stage-6-state-permission-interrupt` 分支完成状态、权限与中断（权限数据模型、PermissionEngine 五模式判定、ASK 停靠与确认恢复、中断清理与状态序列化）。
- 阶段 7 已在 `codex/stage-7-middleware-context` 分支完成中间件与上下文（MiddlewareBase 七钩子、洋葱执行器、BudgetMiddleware、ContextCompressionMiddleware）。下一步是阶段 8：工作空间、MCP 与 Skill。每阶段的详细实施任务见 `docs/superpowers/plans/`。

## 逐章实施计划

阶段 0–3 是已完成工作的中文记录，勾选项表示已经验证；阶段 4–16 是待执行计划。后续实施从规划分支 `codex/stage-plans-zh` 创建阶段 4 分支，再逐章继承，每章只完成该章范围。

| 阶段 | 计划 |
| --- | --- |
| 0 | [固定基线与骨架](docs/superpowers/plans/2026-09-26-stage-0-baseline-skeleton.md) |
| 1 | [消息与响应](docs/superpowers/plans/2026-09-26-stage-1-message-response.md) |
| 2 | [模型抽象](docs/superpowers/plans/2026-09-26-stage-2-model-abstraction.md) |
| 3 | [最小 Agent](docs/superpowers/plans/2026-09-26-stage-3-minimal-agent.md) |
| 4 | [工具调用闭环](docs/superpowers/plans/2026-09-26-stage-4-tool-loop.md) |
| 5 | [事件与流式输出](docs/superpowers/plans/2026-09-26-stage-5-events-streaming.md) |
| 6 | [状态、权限与中断](docs/superpowers/plans/2026-09-26-stage-6-state-permission-interrupt.md) |
| 7 | [中间件与上下文](docs/superpowers/plans/2026-09-26-stage-7-middleware-context.md) |
| 8 | [工作空间、MCP 与 Skill](docs/superpowers/plans/2026-09-26-stage-8-workspace-mcp-skills.md) |
| 9 | [多 Agent 编排](docs/superpowers/plans/2026-09-26-stage-9-multi-agent-orchestration.md) |
| 10 | [应用服务与会话](docs/superpowers/plans/2026-09-26-stage-10-app-session-api.md) |
| 11 | [持久化与分布式存储](docs/superpowers/plans/2026-09-26-stage-11-storage-message-bus.md) |
| 12 | [频道接入与 Web UI](docs/superpowers/plans/2026-09-26-stage-12-channels-web-ui.md) |
| 13 | [RAG 与长期记忆](docs/superpowers/plans/2026-09-26-stage-13-rag-longterm-memory.md) |
| 14 | [远程沙箱](docs/superpowers/plans/2026-09-26-stage-14-remote-sandbox.md) |
| 15 | [A2A 与实时语音](docs/superpowers/plans/2026-09-26-stage-15-a2a-realtime-voice.md) |
| 16 | [可观测性与整体对齐](docs/superpowers/plans/2026-09-26-stage-16-observability-alignment.md) |


## 总原则

1. **先跑通，再扩展。** 第一条主线是“用户消息 → 模型 → Agent 回复”，第二条是“模型要求调用工具 → 执行 → 回填 → 回复”。
2. **依赖从少到多。** 前期用 Fake/Mock 模型，不依赖 API Key、网络、数据库或沙箱服务；真实模型接入在核心循环可测之后。
3. **每步有验收。** 每个阶段保留一个小例子和对应关键测试；跑得通、能解释数据如何流动，才算完成。
4. **不要提前复制全仓库。** 只迁入当前阶段及其必要依赖。可以先做最小实现，随后迁入原项目的完整实现并用原测试验证。
5. **保留原有包名 `agentscope`。** 新旧项目必须使用各自独立的虚拟环境；每次验证导入路径，防止测试意外引用旧项目。
6. **一次一阶段提交。** 提交信息写清本阶段引入的模块与验证结果。复杂功能按可运行切片拆成多个提交。

## 阶段安排

| 阶段 | 学习目标与建议迁入顺序 | 阶段验收 |
| --- | --- | --- |
| 0. 固定基线与骨架 | 记录参考提交；建立 `pyproject.toml`、`src/agentscope/__init__.py`、`tests/`、`examples/`；配置 Python 3.11+、独立虚拟环境与可编辑安装。先保持最小依赖。 | `import agentscope` 成功，导入路径位于 `agentscopeNew`；一个最小测试通过。 |
| 1. 消息和响应 | `message/_block.py`、`message/_base.py`，然后 `model/_model_response.py`、`_model_usage.py`；弄清消息、内容块、工具调用块、模型响应的结构。 | 能创建用户/助手消息，完成基本序列化；对应消息和响应测试通过。 |
| 2. 模型抽象 | `model/_base.py`，用本地 FakeModel 实现相同接口；随后迁入一个真实适配器（建议从现有 `model/_openai_chat` 或 `model/_dashscope` 选一个）和所需 formatter/credential。 | FakeModel 能返回普通文本和工具调用；真实适配器在提供凭据时可跑通一个最小例子。 |
| 3. 最小 Agent | 以 `agent/_agent.py` 为参照，只接通构造、一次模型调用和最终回复；再逐步接入配置与状态。不要一开始复制完整大文件并调试所有分支。 | 不用工具的多轮对话运行；能说清消息进入、模型调用、回复结束的调用链。 |
| 4. 工具闭环 | `tool/_base.py`、`_response.py`、`_toolkit.py`，再接入 Agent 的“请求工具 → 校验参数 → 执行 → 回填结果 → 再问模型”循环。先做一个纯函数工具，后做内置文件工具。 | FakeModel 预设一次工具调用后返回最终答案；成功、参数错误、工具异常三个路径均可验证。 |
| 5. 事件与流式输出 | `event/`、流式模型响应、Agent 事件产生，再做 `console/`。重点理解 start/delta/end 与最终消息的关系。 | 终端可看到增量输出；事件顺序和最终合并结果正确。 |
| 6. 状态、权限与中断 | `state/`、`permission/`，再接入 Agent 的中断、恢复和需要用户确认的工具执行。 | 允许、拒绝、等待确认三种决定行为明确；中断后不会留下无法闭合的工具调用。 |
| 7. 中间件与上下文 | `middleware/_base.py` 及基本生命周期钩子，再加入预算、上下文压缩、注入等具体能力。 | 一个自定义中间件可修改/观察调用；多中间件执行顺序可测试。 |
| 8. 工作空间与外部能力 | `workspace/` 的本地实现、内置 Bash/Read/Write/Edit/Grep/Glob、`mcp/`、`skill/`；远程沙箱后置。 | 本地受控工作空间中的工具可运行；MCP/Skill 各有一个最小示例。 |
| 9. 多 Agent 编排 | `pipeline/`、`sop/`、Agent Teams；先固定流程，再研究动态团队与目标驱动流水线。 | 两个 Agent 可协作完成任务；流水线失败与重试路径可验证。 |
| 10. 应用服务与会话 | `app/` 的服务入口、会话生命周期、Agent 配置、服务 API；先用进程内存储，不引入外部数据库。 | 服务可创建会话、接收消息并返回 Agent 回复；重启和错误路径有明确行为。 |
| 11. 持久化与分布式存储 | `app/storage/`、消息总线和任务状态；从 SQLite/本地实现过渡到 Redis、SQL、S3 等后端，并理解多进程协调。 | 同一会话可恢复；至少一个非内存后端通过读写和故障恢复测试。 |
| 12. 接入频道与 Web UI | 先接 `console/` 以外的服务渠道，再按需加入飞书、Discord、钉钉等频道；最后迁入 `examples/web_ui/` 的前后端。 | 一个外部频道可完成收发；浏览器中可创建会话、发送消息并显示流式结果。 |
| 13. RAG 与长期记忆 | `rag/` 的解析、切块、索引、检索，再接入 `middleware/_longterm_memory/` 的 Mem0/ReMe 等实现。 | 给定一份文档能检索并引用相关片段；跨会话能写入和召回一条长期记忆。 |
| 14. 远程沙箱 | 在本地工作空间稳定后，逐个研究 Docker、E2B、Daytona、K8s 等后端的生命周期和文件/命令接口。 | 至少一个远程后端通过与本地后端相同的工具用例；创建、执行、清理可验证。 |
| 15. A2A 与实时语音 | `agent/_a2a_agent.py` 与相关协议示例；之后接 `agent/_realtime/`、实时模型和音频传输。 | 两个进程的 Agent 可通过 A2A 对话；语音链路可完成一次输入、输出与中断。 |
| 16. 可观测性与整体对齐 | 迁入 `middleware/_tracing/`、指标和日志；补齐多模型适配器，按模块迁入原项目测试并核对公开接口。 | 一次 Agent 调用可追踪到模型与工具步骤；选定范围的测试通过，并记录尚未覆盖的功能。 |

## 每一阶段的固定工作流

1. 阅读该阶段公开接口、实现文件和对应测试，只画出当前功能的最短调用链。
2. 写一个最多几十行的使用例子，明确预期输出。
3. 在新仓库迁入必需代码及直接依赖，先让例子运行；不要为了消除导入错误而批量复制所有模块。
4. 从参考项目迁入对应测试，必要时仅调整测试环境/fixture，不随意修改被学习的业务逻辑。
5. 运行本阶段测试和前面阶段的回归测试；记录学到的关键设计、未解决的问题和与参考项目的差异。
6. 提交当前阶段。下一阶段开始前确保新项目能在干净环境中安装。

## 第一周的具体任务

1. 固定参考提交 `5ff52f8`，确认是否还要包含参考仓库中的未提交改动。
2. 在 `agentscopeNew` 建立最小 `src` 布局和独立虚拟环境；执行可编辑安装，并打印 `agentscope.__file__` 验证来源。
3. 从 `message` 模块开始：梳理 `Msg`、`UserMsg`、`AssistantMsg`、`TextBlock`、`ToolCallBlock`、`ToolResultBlock` 的关系。
4. 迁入消息结构与最小测试，写 `examples/message_demo.py` 展示用户输入、助手文本和一次工具调用的数据形态。
5. 在阶段 1 验收后，再开始 FakeModel 与模型响应；暂不接真实 API。

## 参考入口

- 项目说明：`D:\code\agentscope\README_zh.md`
- 包与依赖：`D:\code\agentscope\pyproject.toml`
- 第一条执行主线：`src/agentscope/message/` → `model/` → `agent/_agent.py` → `tool/`
- 对应测试：`tests/message_test.py`、`tests/model_response_test.py`、`tests/agent_basic_test.py`、`tests/toolkit_test.py`
- 现有架构阅读材料：`docs/architecture_analysis/`。阅读顺序可参考，但动手实现按本计划的依赖顺序进行。
