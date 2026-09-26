# 阶段 4：工具调用闭环实施计划

> **供执行本计划的 Agent 使用：** 依照 `writing-plans` 的要求，逐任务执行并勾选。执行时使用 `superpowers:executing-plans`；本仓库由当前 Agent 原生实施，除非用户另行要求，不派发子 Agent。

**目标：** 让 Agent 完成一次或多次“模型提出工具调用 → 参数校验 → 工具执行 → 结果回填 → 模型给出最终答复”的离线闭环。

**架构：** 以参考的 ToolBase、ToolChunk、ToolResponse、Toolkit 为接口目标，先实现纯函数工具和统一结果，再把循环接入现有 Agent.reply。工具错误作为可观察的结果回填，模型调用次数由 max_iters 限制。

**技术栈：** Python 3.11、Pydantic 2、jsonschema、pytest、FakeChatModel。

**规格：** 根目录 `PLAN.md` 的阶段 4；固定参考版本见 `BASELINE.md`。参考入口：`src/agentscope/tool/_base.py`、`src/agentscope/tool/_response.py`、`src/agentscope/tool/_toolkit.py`、`src/agentscope/tool/_types.py`、`tests/toolkit_test.py`、`tests/agent_basic_test.py`。

## 全局约束

- 从 `codex/stage-plans-zh` 创建 `codex/stage-4-tool-loop`，保持前一阶段测试通过；计划文件先提交到规划分支，实施时随阶段分支继承。
- 运行命令使用 `.\.conda\python.exe`；验证 `agentscope.__file__` 位于 `D:\code\agentscopeNew`。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入源码保留许可与署名。
- 阶段 3 的纯文本回复行为必须保持通过；新增工具功能不依赖外部服务。
- 保留 ToolCallBlock 的 id/name/arguments 与 ToolResultBlock 的对应关系，结果顺序稳定。
- 先只接本地、非流式工具；工具权限在阶段 6，MCP 与工作空间工具在阶段 8。
- 循环必须有显式 max_iters，达到上限不得无限请求模型。

## 复核重点

1. 未知工具名返回可识别的失败结果，Agent 不崩溃。
2. 无效 JSON 或缺必填参数不会执行工具。
3. 工具抛异常后调用链仍能得到失败结果并进入下一轮。
4. 同一回复内多个调用按请求顺序记录结果。
5. 重复 tool_call_id 不得让结果错误关联。

---

### 任务 1：工具协议与结果

**文件：** 新建 src/agentscope/tool/_base.py、_response.py、__init__.py；测试 tests/test_tool.py。

**接口：** ToolBase.name/description/input_schema；async ToolBase.call(**kwargs) -> ToolChunk；ToolChunk、ToolResponse 与 ToolResultState。

- [ ] **步骤 1：写失败测试。** `test_tool_result_shape`：断言成功与异常结果均可转为 ToolResultBlock，保留 tool_call_id，空结果不共享可变列表。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_tool.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 实现上述类和最小结果转换；按参考的 ToolChunk/ToolResponse 语义保留结构化内容与状态。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_tool.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage4): 工具协议与结果`；每章完成后推送 `codex/stage-4-tool-loop`。

### 任务 2：注册、校验与调度

**文件：** 新建 src/agentscope/tool/_toolkit.py；测试 tests/test_toolkit.py。

**接口：** Toolkit(tools: list[ToolBase] | None = None)；async get_tool_schemas(groups: list[str] | None = None) -> list[dict]；call_tool(tool_call: ToolCallBlock, state: AgentState) -> AsyncGenerator[ToolChunk | ToolResponse, None]。

- [ ] **步骤 1：写失败测试。** `test_toolkit_dispatch`：注册 add 工具后 2+3 得 5；未知工具、非法 JSON、缺少参数、工具异常四种输入分别断言失败状态且调用计数不误增；重复 tool_call_id 的结果不得串联。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_toolkit.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 注册时检查重名；调用时解析参数、用 input_schema 校验，再执行工具并标准化异常。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_toolkit.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage4): 注册、校验与调度`；每章完成后推送 `codex/stage-4-tool-loop`。

### 任务 3：Agent 推理与行动循环

**文件：** 修改 src/agentscope/agent/_agent.py；测试 tests/test_agent_tool_loop.py。

**接口：** Agent(..., toolkit: Toolkit | None = None, max_iters: int = 10)；reply(inputs) -> AssistantMsg；复用 ChatModelBase.__call__(messages, tools=...)。

- [ ] **步骤 1：写失败测试。** `test_one_tool_round`：Fake 模型先返回 add 调用再返回文本，断言模型收到工具结果、最终回复文本和上下文次序；test_max_iters 断言连续调用在上限停止。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_tool_loop.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 每轮把可用工具 schema 交给模型；将助手工具调用及对应结果写入上下文，继续调用直至文本完成或达到上限。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_tool_loop.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage4): Agent 推理与行动循环`；每章完成后推送 `codex/stage-4-tool-loop`。

### 任务 4：示例、回归与提交

**文件：** 新建 examples/tool_demo.py；修改 README.md、PLAN.md；测试 tests/test_tool_demo.py。

**接口：** 示例只用 FakeChatModel 和本地 add 工具，可直接运行。

- [ ] **步骤 1：写失败测试。** `test_tool_demo`：子进程运行示例，断言退出码 0、最终答案包含 5；全量 tests 保持通过。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_tool_demo.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 写清一次工具调用的数据流、状态与尚未接入的权限/流式边界；在独立阶段分支提交并推送。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_tool_demo.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage4): 示例、回归与提交`；每章完成后推送 `codex/stage-4-tool-loop`。

## 章末验收与暂缓

- 验收：本章示例可离线运行，相关测试与累计回归通过；在 README 记录调用链、与固定参考提交的差异和测试结果。
- 暂缓：仅实现本章列出的纵向切片。完整提供商适配、外部基础设施及后续阶段能力 按 `PLAN.md` 的后续章节推进。
- 自查：逐项核对 `PLAN.md` 阶段 4 的验收、文件职责、接口名、上述五类失败输入及对应测试；若参考实现接口与计划不同，先更新本计划再实施。
