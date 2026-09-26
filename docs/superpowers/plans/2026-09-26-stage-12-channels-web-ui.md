# 阶段 12：频道接入与 Web UI实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 的步骤逐任务勾选；实施方法为 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 让一个外部频道可完成消息收发，并提供浏览器会话页展示流式答复。

**架构：** 频道事件映射为会话服务输入与出站消息，先用本地 Mock 频道测试，再接一个真实提供商适配器。Web UI 消费阶段 10–11 的 API 和阶段 5 的事件流，状态归属在服务端。

**技术栈：** Python 3.11、FastAPI、pytest；参考 Web UI 的前端构建工具。

**规格：** `PLAN.md` 阶段 12、`BASELINE.md`。固定参考提交的入口：`src/agentscope/app/channel/_base.py`、`src/agentscope/app/channel/_gateway.py`、`src/agentscope/app/channel/_feishu/_channel.py`、`src/agentscope/app/channel/_discord/_channel.py`、`src/agentscope/app/channel/_dingtalk/_channel.py`、`src/agentscope/app/_router/_channel.py`、`tests/channel_gateway_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-12-channels-web-ui`；每项功能完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- 频道密钥只来自本地配置/环境变量，日志和响应脱敏。
- 频道 webhook 验签、幂等和会话路由在发给 Agent 前完成。
- Web UI 先在本地验证，不要求公网部署。
- 飞书、Discord、钉钉至少完成一个，其余记录未覆盖项。

## 复核重点

1. 无效签名/过期时间戳拒绝入站。
2. 重复 webhook 不触发两次 Agent 回复。
3. 同一用户不同频道的会话不串线。
4. 断开的浏览器流可重新拉取最终消息。
5. 出站发送失败保留重试状态。

---

### 任务 1：频道事件与网关

**文件：** 新建 src/agentscope/app/channel/_base.py、_gateway.py、_routing.py、__init__.py；测试 tests/test_channel_gateway.py。

**接口：** ChannelEvent(channel_id, external_user_id, message_id, text)；ChannelGateway.receive(event) -> session_id；ChannelBase.send(target, text)。

- [ ] **步骤 1：写失败测试。** test_route_and_dedupe：同用户/频道定位同会话，不同频道分离；同 message_id 重投只产生一次聊天调用。 测试写入 `tests/test_channel_gateway.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_channel_gateway.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 统一入站数据、会话路由与幂等键，出站失败记录状态。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_channel_gateway.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage12): 频道事件与网关` 作为提交信息；最后推送 `codex/stage-12-channels-web-ui`。

### 任务 2：一个真实频道适配器

**文件：** 新建 src/agentscope/app/channel/_feishu/_channel.py、__init__.py；测试 tests/test_channel_feishu.py。

**接口：** FeishuChannel.verify(payload, signature, timestamp) -> ChannelEvent；send(target, text)；名称按参考提交核实。

- [ ] **步骤 1：写失败测试。** test_feishu_verify：Mock 请求合法签名被接受；错误签名与过期时间戳拒绝；出站 Mock 响应映射正确。 测试写入 `tests/test_channel_feishu.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_channel_feishu.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 以参考飞书适配器为样本；真实凭据联调写成手动验收步骤。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_channel_feishu.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage12): 一个真实频道适配器` 作为提交信息；最后推送 `codex/stage-12-channels-web-ui`。

### 任务 3：流式 API 和前端

**文件：** 修改 src/agentscope/app/_router/_chat.py；新建 examples/web_ui/ 的最小前端与 tests/test_web_stream.py。

**接口：** GET /sessions/{session_id}/events 返回 SSE；前端创建会话、发消息、消费增量与最终消息。

- [ ] **步骤 1：写失败测试。** test_sse_sequence：HTTP 客户端收到 start/delta/end 且最终文本只出现一次；浏览器手动验收创建会话与断线恢复。 测试写入 `tests/test_web_stream.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_web_stream.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 复用 Agent.reply_stream 事件，保留事件 ID 用于恢复。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_web_stream.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage12): 流式 API 和前端` 作为提交信息；最后推送 `codex/stage-12-channels-web-ui`。

### 任务 4：示例与回归

**文件：** 新建 examples/channel_demo.py、tests/test_channel_demo.py；修改 README.md、PLAN.md。

**接口：** MockChannel 用同一网关完成入站到出站的离线流程。

- [ ] **步骤 1：写失败测试。** test_channel_demo：无凭据运行退出码 0；后端全量 tests 与前端构建通过。 测试写入 `tests/test_channel_demo.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_channel_demo.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 记录真实频道配置、回调地址和 Web UI 本地启动步骤；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_channel_demo.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage12): 示例与回归` 作为提交信息；最后推送 `codex/stage-12-channels-web-ui`。

## 章末验收与暂缓

- 验收：示例可按本章约束运行；计划内成功、错误和恢复路径可被测试；累计回归通过，README 记录数据流及固定参考版本的差异。
- 暂缓：本章未列出的适配器、频道或高级特性由 `PLAN.md` 的后续阶段处理。
- 自查：逐条对应 `PLAN.md` 阶段 12 的目标；复核文件职责、接口名称、五项风险和测试断言。若与参考接口不符，先修订本计划，再执行。
