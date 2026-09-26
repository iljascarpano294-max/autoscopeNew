# 阶段 6：状态、权限与中断实施计划

> **供执行本计划的 Agent 使用：** 依照 `writing-plans` 的要求，逐任务执行并勾选。执行时使用 `superpowers:executing-plans`；本仓库由当前 Agent 原生实施，除非用户另行要求，不派发子 Agent。

**目标：** 让工具执行具备允许、拒绝、等待确认三种决策，并使中断与恢复可被保存和验证。

**架构：** 扩展 AgentState 保存待处理工具调用；PermissionEngine 在工具执行前判定；ASK 产生确认事件，恢复时只处理匹配请求。中断用显式终止事件和状态转换。

**技术栈：** Python 3.11、Pydantic 2、pytest、asyncio。

**规格：** 根目录 `PLAN.md` 的阶段 6；固定参考版本见 `BASELINE.md`。参考入口：`src/agentscope/state/_state.py`、`src/agentscope/permission/_types.py`、`src/agentscope/permission/_rule.py`、`src/agentscope/permission/_decision.py`、`src/agentscope/permission/_context.py`、`src/agentscope/permission/_engine.py`、`src/agentscope/event/_event.py`、`tests/permission_engine_test.py`、`tests/agent_interrupt_test.py`。

## 全局约束

- 每章从上一阶段分支创建 `codex/stage-6-state-permission-interrupt`，保持前一阶段测试通过；计划文件先提交到规划分支，实施时随阶段分支继承。
- 运行命令使用 `.\.conda\python.exe`；验证 `agentscope.__file__` 位于 `D:\code\agentscopeNew`。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入源码保留许可与署名。
- 阶段 4 的工具闭环在 ALLOW 模式下保持可运行。
- 默认规则与模式按固定参考提交核对；拒绝和待确认均不调用实际工具。
- 待确认记录包含 tool_call_id 和参数摘要，恢复只接受匹配决定。
- 状态序列化不得包含 API Key 或服务器密码。

## 复核重点

1. DENY 优先于 ALLOW，且绝不调用工具。
2. ASK 在未获确认时不得继续执行或伪造工具结果。
3. 重复提交同一确认不得执行两次。
4. 取消后所有待处理调用必须有可解释状态。
5. 恢复时调用 ID 不匹配应被拒绝。

---

### 任务 1：权限数据模型

**文件：** 新建 src/agentscope/permission/_types.py、_rule.py、_decision.py、_context.py、__init__.py；测试 tests/test_permission.py。

**接口：** PermissionMode、PermissionBehavior、PermissionRule、PermissionContext、PermissionDecision；字段与参考同名。

- [ ] **步骤 1：写失败测试。** `test_permission_types`：枚举可序列化；规则携带工具名和行为；缺工具名或非法行为明确失败。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_permission.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 迁入本阶段必需类型，不提前引入文件系统和命令匹配的所有规则。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_permission.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage6): 权限数据模型`；每章完成后推送 `codex/stage-6-state-permission-interrupt`。

### 任务 2：规则求值

**文件：** 新建 src/agentscope/permission/_engine.py；测试 tests/test_permission_engine.py。

**接口：** PermissionEngine(context)；async check_permission(tool: ToolBase, tool_input: dict) -> PermissionDecision。

- [ ] **步骤 1：写失败测试。** `test_decision_order`：同一工具同时命中拒绝与允许时为 DENY；只读工具按模式允许；无规则的写工具在默认模式为 ASK。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_permission_engine.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 按参考模式顺序实现判定，保留工具自定义安全检查入口。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_permission_engine.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage6): 规则求值`；每章完成后推送 `codex/stage-6-state-permission-interrupt`。

### 任务 3：待确认与状态恢复

**文件：** 修改 src/agentscope/state/_state.py、src/agentscope/agent/_agent.py、src/agentscope/event/_event.py；测试 tests/test_agent_confirmation.py。

**接口：** RequireUserConfirmEvent、UserConfirmResultEvent、UserInterruptEvent；Agent.reply_stream 接受恢复事件。

- [ ] **步骤 1：写失败测试。** `test_confirm_resume`：ASK 后工具调用次数为 0；允许后为 1；重复确认和错误 ID 均不增加；拒绝转为失败结果。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_confirmation.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 保存 pending 调用及上下文位置，恢复时做 ID 校验并保证一次执行。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_confirmation.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage6): 待确认与状态恢复`；每章完成后推送 `codex/stage-6-state-permission-interrupt`。

### 任务 4：中断、序列化和示例

**文件：** 新建 examples/permission_demo.py、tests/test_agent_interrupt.py；修改 README.md、PLAN.md。

**接口：** AgentState.model_dump_json()/model_validate_json() 可往返待确认状态。

- [ ] **步骤 1：写失败测试。** `test_interrupt_cleanup`：工具调用前中断不执行工具，状态可序列化且后续新一轮仍可运行；全量 tests 通过。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_interrupt.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 示范允许、拒绝、确认与中断路径；提交并推送阶段分支。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_interrupt.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage6): 中断、序列化和示例`；每章完成后推送 `codex/stage-6-state-permission-interrupt`。

## 章末验收与暂缓

- 验收：本章示例可离线运行，相关测试与累计回归通过；在 README 记录调用链、与固定参考提交的差异和测试结果。
- 暂缓：仅实现本章列出的纵向切片。完整提供商适配、外部基础设施及后续阶段能力 按 `PLAN.md` 的后续章节推进。
- 自查：逐项核对 `PLAN.md` 阶段 6 的验收、文件职责、接口名、上述五类失败输入及对应测试；若参考实现接口与计划不同，先更新本计划再实施。
