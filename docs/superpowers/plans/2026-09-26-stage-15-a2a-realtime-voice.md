# 阶段 15：A2A 与实时语音实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 逐任务执行并勾选；实施时使用 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 完成两个进程间 Agent 的 A2A 对话，以及一条可中断的实时音频输入输出链路。

**架构：** 先把 Agent 包装为可调用的 A2A 服务与客户端，用 Mock transport 测试协议；再建立实时会话事件、音频传输与聚合器。Fake 音频模型负责离线验收，真实模型适配器单独联调。

**技术栈：** Python 3.11、asyncio、FastAPI/httpx、A2A SDK、WebSocket、pytest。

**规格：** `PLAN.md` 阶段 15、`BASELINE.md`。固定参考提交的入口：`src/agentscope/agent/_a2a_agent.py`、`src/agentscope/state/_a2a_state.py`、`src/agentscope/agent/_realtime/_agent.py`、`src/agentscope/agent/_realtime/_aggregator.py`、`src/agentscope/realtime/_base.py`、`src/agentscope/realtime/_events.py`、`src/agentscope/realtime/_transport/_local.py`、`tests/a2a_agent_test.py`、`tests/realtime_agent_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-15-a2a-realtime-voice`；每项完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- A2A 请求有超时、关联 ID 和明确取消行为。
- 音频数据/事件分片顺序可验证；测试不依赖麦克风或真实模型。
- 实时会话断线后释放传输和模型资源。
- 真实语音 API Key 只从本机秘密来源注入，不写入计划和代码。

## 复核重点

1. 重复 A2A 消息 ID 不重复触发远端行动。
2. 远端超时不会使本地 Agent 永久挂起。
3. 乱序音频/文本事件被拒绝或明确重排。
4. 用户打断后旧音频不继续播放。
5. 断线重连不重复提交最终消息。

---

### 任务 1：A2A 协议状态

**文件：** 新建 src/agentscope/state/_a2a_state.py、src/agentscope/agent/_a2a_agent.py；测试 tests/test_a2a_agent.py。

**接口：** A2AAgent(endpoint, timeout).reply_stream(inputs) -> AsyncGenerator[AgentEvent | Msg, None]；A2AState 保存任务 ID 与对端状态。

- [ ] **步骤 1：写失败测试。** test_a2a_mock：Mock transport 返回事件流，最终消息正确；重复消息 ID 只执行一次；超时有终止事件。 测试写入 `tests/test_a2a_agent.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_a2a_agent.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 将本地消息映射为 A2A 协议请求和响应，关联 task_id/session_id。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_a2a_agent.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage15): A2A 协议状态` 作为提交信息；最后推送 `codex/stage-15-a2a-realtime-voice`。

### 任务 2：两进程端到端

**文件：** 新建 examples/a2a_server.py、examples/a2a_client.py、tests/test_a2a_e2e.py。

**接口：** 服务进程暴露 A2A 能力描述与任务接口，客户端通过 A2AAgent 调用。

- [ ] **步骤 1：写失败测试。** test_a2a_e2e：本地启动两进程，以 Fake 模型完成一轮对话并退出；异常进程能被回收。 测试写入 `tests/test_a2a_e2e.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_a2a_e2e.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 真实网络仅绑定本机回环地址，流程可由单条测试命令复现。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_a2a_e2e.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage15): 两进程端到端` 作为提交信息；最后推送 `codex/stage-15-a2a-realtime-voice`。

### 任务 3：实时事件与音频聚合

**文件：** 新建 src/agentscope/realtime/_base.py、_events.py、_transport/_local.py、src/agentscope/agent/_realtime/_aggregator.py；测试 tests/test_realtime_aggregator.py。

**接口：** RealtimeModelBase.send_audio/receive_events/close；RealtimeAggregator.consume(event) -> transcript/audio chunks。

- [ ] **步骤 1：写失败测试。** test_realtime_order：输入两段音频得到一段转写和有序输出；乱序片段报错；中断后旧输出被丢弃。 测试写入 `tests/test_realtime_aggregator.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_realtime_aggregator.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 分开会话状态与传输，先用本地队列传输验证事件语义。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_realtime_aggregator.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage15): 实时事件与音频聚合` 作为提交信息；最后推送 `codex/stage-15-a2a-realtime-voice`。

### 任务 4：实时 Agent 与示例

**文件：** 新建 src/agentscope/agent/_realtime/_agent.py、examples/realtime_demo.py、tests/test_realtime_agent.py；修改 README.md、PLAN.md、pyproject.toml。

**接口：** RealtimeAgent.start/interrupt/close；Fake 实时模型无需音频设备。

- [ ] **步骤 1：写失败测试。** test_voice_roundtrip：Fake 输入音频触发一次文本+音频输出；interrupt 后停止播放且 close 可重复；全量 tests 通过。 测试写入 `tests/test_realtime_agent.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_realtime_agent.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 记录 OpenAI/Gemini/DashScope 真实适配器需后续逐个对齐；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_realtime_agent.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage15): 实时 Agent 与示例` 作为提交信息；最后推送 `codex/stage-15-a2a-realtime-voice`。

## 章末验收与暂缓

- 验收：本章示例和分支目标可复现；成功、失败、恢复路径有测试；累计回归通过，README 记录调用链与固定参考版本的差异。
- 暂缓：本章未列出的平台/适配器/外部集成继续保留在 `PLAN.md`，不把它们视作已完成。
- 自查：逐条对应 `PLAN.md` 阶段 15；复核文件职责、接口名、五项风险和测试断言。若与参考接口不符，先修订本计划，再实施。
