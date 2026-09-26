# 阶段 9：多 Agent 编排实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 的步骤逐任务勾选；实施方法为 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 让两个 Agent 按固定流程协作，并在失败、重试和恢复时保持状态可解释。

**架构：** 先定义可替换 Agent 的 PipelineProtocol，再实现 SOP 顺序步骤和状态；最后以两 Agent 的确定性例子验证消息传递。动态团队和目标驱动编排建立在稳定的固定流程之上。

**技术栈：** Python 3.11、Pydantic 2、asyncio、pytest、FakeChatModel。

**规格：** `PLAN.md` 阶段 9、`BASELINE.md`。固定参考提交的入口：`src/agentscope/pipeline/_base.py`、`src/agentscope/pipeline/_goal_pipeline.py`、`src/agentscope/sop/_schema.py`、`src/agentscope/sop/_state.py`、`src/agentscope/sop/_engine.py`、`tests/sop_engine_test.py`、`tests/pipeline_goal_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-9-multi-agent-orchestration`；每项功能完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- 复用阶段 5 的 AgentEvent | Msg 事件流。
- 每个 Agent 独立上下文；跨 Agent 传递消息记录来源。
- 失败重试预算有限；恢复前校验 SOP 结构未变化。
- 动态团队工具不提前引入 app 服务和数据库。

## 复核重点

1. 某步失败时后续步骤不误执行。
2. 重试达到上限后状态明确结束。
3. 恢复状态与当前步骤数不一致时拒绝继续。
4. 两个 Agent 不共享可变上下文。
5. 用户确认挂起后恢复只进入原步骤。

---

### 任务 1：流水线协议

**文件：** 新建 src/agentscope/pipeline/_base.py、__init__.py；测试 tests/test_pipeline_protocol.py。

**接口：** PipelineProtocol.reply_stream(inputs) -> AsyncGenerator[AgentEvent | Msg, None]；Agent 满足此协议。

- [ ] **步骤 1：写失败测试。** test_agent_as_pipeline：把 Agent 交给接受 PipelineProtocol 的调用者，事件与最终 Msg 顺序不变。 测试写入 `tests/test_pipeline_protocol.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_pipeline_protocol.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 以 Protocol 定义最小执行边界，避免编排层依赖 Agent 私有字段。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_pipeline_protocol.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage9): 流水线协议` 作为提交信息；最后推送 `codex/stage-9-multi-agent-orchestration`。

### 任务 2：SOP 模式和状态

**文件：** 新建 src/agentscope/sop/_schema.py、_state.py、__init__.py；测试 tests/test_sop_state.py。

**接口：** SOP、SOPStep、SOPRunState、SOPPhase；状态可 JSON 往返。

- [ ] **步骤 1：写失败测试。** test_sop_state_roundtrip：两步骤中第一步完成、第二步等待时往返后阶段和步骤索引一致；步骤数不符抛 ValueError。 测试写入 `tests/test_sop_state.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_sop_state.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 以 Pydantic 描述步骤和状态，记录尝试次数与当前阶段。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_sop_state.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage9): SOP 模式和状态` 作为提交信息；最后推送 `codex/stage-9-multi-agent-orchestration`。

### 任务 3：顺序执行与恢复

**文件：** 新建 src/agentscope/sop/_engine.py；测试 tests/test_sop_engine.py。

**接口：** SOPEngine(sop, state=None).reply_stream(inputs) -> AsyncGenerator[AgentEvent | Msg, None]。

- [ ] **步骤 1：写失败测试。** test_two_agents：规划 Agent 产出文本供执行 Agent 使用，最终结果由第二个 Agent 给出；失败重试、确认挂起恢复和预算耗尽分别有断言。 测试写入 `tests/test_sop_engine.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_sop_engine.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 按步骤顺序驱动 PipelineProtocol，待确认时持久化状态并停止流，恢复时定位原步骤。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_sop_engine.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage9): 顺序执行与恢复` 作为提交信息；最后推送 `codex/stage-9-multi-agent-orchestration`。

### 任务 4：目标编排切片与示例

**文件：** 新建 src/agentscope/pipeline/_goal_pipeline.py、examples/team_demo.py、tests/test_goal_pipeline.py；修改 README.md、PLAN.md。

**接口：** GoalPipeline 接受两个具名 Agent 和目标描述，输出事件流。

- [ ] **步骤 1：写失败测试。** test_goal_pipeline：成员失败后给出可追踪失败事件；正常路径两个成员各执行一次；示例与全量 tests 通过。 测试写入 `tests/test_goal_pipeline.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_goal_pipeline.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 仅做可控的双 Agent 目标流程；动态增删成员先以进程内状态表示，提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_goal_pipeline.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage9): 目标编排切片与示例` 作为提交信息；最后推送 `codex/stage-9-multi-agent-orchestration`。

## 章末验收与暂缓

- 验收：示例可按本章约束运行；计划内成功、错误和恢复路径可被测试；累计回归通过，README 记录数据流及固定参考版本的差异。
- 暂缓：本章未列出的适配器、频道或高级特性由 `PLAN.md` 的后续阶段处理。
- 自查：逐条对应 `PLAN.md` 阶段 9 的目标；复核文件职责、接口名称、五项风险和测试断言。若与参考接口不符，先修订本计划，再执行。
