# 阶段 3：最小 Agent实施计划

> **供执行本计划的 Agent 使用：** 本章已由当前 Agent 原生执行。按 `writing-plans` 格式保留任务与勾选状态；后续复核时按 `superpowers:executing-plans` 的逐任务方式检查。

**目标：** 提供能接收消息、携带系统提示和对话上下文、完成非流式多轮文本回复的 Agent。

**架构：** AgentState 持有对话上下文；Agent.reply 保存输入、调用 ChatModelBase、把 ChatResponse 转为 AssistantMsg 后存回状态。工具循环、事件与中间件留待后续阶段，当前遇到工具调用会明确报未实现。

**技术栈：** Python 3.11、Pydantic 2、阶段 1 消息、阶段 2 模型抽象、pytest。

**规格：** `PLAN.md` 阶段 3；`BASELINE.md` 固定参考提交。

## 全局约束

- 保留 agentscope.agent.Agent、Agent.reply、Agent.observe 和 Agent.state.context。
- 不整体复制参考的大型 _agent.py；其工具、事件、权限和中间件依赖分阶段引入。
- 测试与示例使用 Fake 模型，无 API Key、Redis 或外网。
- 上下文只存用户与助手对话；每轮模型调用重新构造系统消息。

## 复核重点

1. 第二轮模型输入包含第一轮的用户和助手消息且顺序正确。
2. 两个 Agent 实例的上下文隔离。
3. observe 只保存消息，不调用模型。
4. 工具调用响应必须明确失败，不谎称已执行。
5. 模型失败时不写入伪助手回复。

---

### 任务 1：隔离的对话状态

**文件：** 新建 src/agentscope/state/_state.py、__init__.py；测试 tests/test_agent.py。

**接口：** AgentState(context: list[Msg] = [])，每个实例拥有独立列表。

- [x] **步骤 1：编写失败测试。** test_agent_state_isolation：两个 AgentState 不共享 context；注入 Agent 后保留传入状态。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 用 Pydantic default_factory 建立独立默认列表。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 2：多轮回复与观察

**文件：** 新建 src/agentscope/agent/_agent.py、__init__.py；扩展 tests/test_agent.py。

**接口：** Agent(name, system_prompt, model, state=None)；await reply(inputs: Msg | list[Msg] | None) -> Msg；await observe(msgs: Msg | list[Msg] | None) -> None。

- [x] **步骤 1：编写失败测试。** test_multi_turn_reply 等：断言模型输入顺序、状态累计、observe、工具调用拒绝与模型失败时状态。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 实现最小非流式路径，并把 ChatUsage 映射到消息 Usage。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 3：示例与累计验证

**文件：** 新建 examples/agent_demo.py；修改 README.md、PLAN.md。

**接口：** 使用 FakeChatModel 展示两轮离线对话。

- [x] **步骤 1：编写失败测试。** 运行示例、全量 tests 和 pip check：21 个测试通过，依赖检查无冲突。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 文档解释输入 → 状态 → 模型 → 回复的数据流；已在阶段 3 分支提交并推送。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：提交阶段结果。** 已提交并推送 `codex/stage-3-minimal-agent`，提交 `0484f58`。

## 章末验收与暂缓

- 已验证：本章示例与累计测试通过；导入来自 `D:\code\agentscopeNew`。
- 暂缓：与本阶段无关的工具执行、流式事件、权限、服务及外部基础设施按 `PLAN.md` 的后续章节推进。
- 自查：本计划的接口、测试、文件范围与阶段 3 已实现代码一致；保持已完成标记，不把历史任务重新列为待办。
