# 阶段 1：消息与响应实施计划

> **供执行本计划的 Agent 使用：** 本章已由当前 Agent 原生执行。按 `writing-plans` 格式保留任务与勾选状态；后续复核时按 `superpowers:executing-plans` 的逐任务方式检查。

**目标：** 建立可序列化的消息块、角色消息和模型响应容器，不调用模型 API。

**架构：** 消息与内容块由 Pydantic 负责验证及序列化；模型响应和用量保存一次调用的数据形态。公开导出采用本阶段需要的 agentscope.message 与 agentscope.model 名称。

**技术栈：** Python 3.11、Pydantic 2、pytest。

**规格：** `PLAN.md` 阶段 1；`BASELINE.md` 固定参考提交。

## 全局约束

- 保留 agentscope 包名和独立 .conda 环境。
- 本阶段无 API Key、网络、数据库或模型调用。
- 角色与块类型参照固定参考提交；事件应用、权限和流式执行延后。
- 只导出本阶段实际使用的名称。

## 复核重点

1. 用户消息中的工具调用块与系统消息中的非文本块应被拒绝。
2. 显式 ID 和 metadata 在序列化后保留。
3. 两个消息或响应实例不共享默认列表。
4. ChatResponse.is_last 可正确序列化。
5. 提取纯文本时忽略非文本块。

---

### 任务 1：消息块与角色验证

**文件：** 新建 src/agentscope/message/_block.py、_base.py、__init__.py；测试 tests/test_message.py。

**接口：** TextBlock、ThinkingBlock、ToolCallBlock、ToolResultBlock、DataBlock；Msg、UserMsg、AssistantMsg、SystemMsg；Msg.get_text_content()。

- [x] **步骤 1：编写失败测试。** test_message_roundtrip 等：断言构造、JSON 往返、显式 ID、独立默认值、提取文本与非法角色块组合。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_message.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 使用 Pydantic 实现带类型区分的块与消息构造，按角色约束允许的块类型。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_message.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 2：模型响应与用量

**文件：** 新建 src/agentscope/model/_model_response.py、_model_usage.py、__init__.py；测试 tests/test_model_response.py。

**接口：** ChatResponse(content, is_last)、ChatUsage(input_tokens, output_tokens, time)、FinishedReason、StructuredResponse；ChatResponse.append_text(text, block_id=None)。

- [x] **步骤 1：编写失败测试。** test_model_response_roundtrip 等：断言 is_last、usage、独立默认 content、按 block_id 累加文本。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_response.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 实现响应容器，不导入提供商或工具执行模块。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_response.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 3：数据形态示例与累计验证

**文件：** 新建 examples/message_demo.py；修改 README.md、PLAN.md。

**接口：** 示例展示用户消息、助手文本和一次工具调用的数据形态；工具只作为数据。

- [x] **步骤 1：编写失败测试。** 运行示例退出码 0；全量测试 9 个通过。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 记录数据流与暂缓功能；已在阶段 1 分支提交并推送。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：提交阶段结果。** 已提交并推送 `codex/stage-1-message-response`，提交 `590fde9`。

## 章末验收与暂缓

- 已验证：本章示例与累计测试通过；导入来自 `D:\code\agentscopeNew`。
- 暂缓：与本阶段无关的工具执行、流式事件、权限、服务及外部基础设施按 `PLAN.md` 的后续章节推进。
- 自查：本计划的接口、测试、文件范围与阶段 1 已实现代码一致；保持已完成标记，不把历史任务重新列为待办。
