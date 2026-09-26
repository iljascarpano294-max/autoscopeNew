# 阶段 2：模型抽象实施计划

> **供执行本计划的 Agent 使用：** 本章已由当前 Agent 原生执行。按 `writing-plans` 格式保留任务与勾选状态；后续复核时按 `superpowers:executing-plans` 的逐任务方式检查。

**目标：** 让阶段 1 的消息通过统一模型接口、确定性 Fake 模型和一个 OpenAI Chat Completions 适配器。

**架构：** ChatModelBase 负责重试和取消；子类实现具体调用。Formatter 把 Msg 映射到提供商消息；OpenAI 适配器把文本与工具调用映射回 ChatResponse，测试使用无网络传输。

**技术栈：** Python 3.11、Pydantic 2、OpenAI SDK、httpx MockTransport、pytest。

**规格：** `PLAN.md` 阶段 2；`BASELINE.md` 固定参考提交。

## 全局约束

- 保留本阶段需要的 agentscope.model 与 agentscope.credential 公开名称。
- 自动化测试不要求真实 API Key 或外网。
- 工具调用在本章只是数据；工具执行属于阶段 4。
- 流式输出、结构化输出、模型卡与其他提供商参数延后。

## 复核重点

1. 可重试错误不能无限重试或偷消耗响应。
2. 不可重试错误立即抛出。
3. 取消模型调用产生中断响应。
4. Formatter 不把工具调用块放进用户消息。
5. 适配器保留工具调用的 ID、名称和参数。

---

### 任务 1：模型基类与 Fake 模型

**文件：** 新建 src/agentscope/model/_base.py、_fake.py；修改 model/__init__.py；测试 tests/test_model_base.py。

**接口：** ChatModelBase.__call__(messages, tools=None, tool_choice=None) -> ChatResponse；子类 _call_api(...)；FakeChatModel(responses) 每次消耗一个预设响应。

- [x] **步骤 1：编写失败测试。** test_fake_model_and_retry 等：断言文本/工具响应、输入记录、重试预算、立即失败与取消。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_base.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 基类统一重试和取消；Fake 模型按队列返回确定性结果。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_base.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 2：真实适配器的无网络验证

**文件：** 新建 credential/_openai.py、formatter/_openai.py、model/_openai_chat/_model.py 及对应 __init__.py；修改 pyproject.toml；测试 tests/test_openai_adapter.py。

**接口：** OpenAICredential(api_key, base_url=None)、OpenAIChatFormatter.format(messages)、OpenAIChatModel(credential, model, ..., client_kwargs=None)。

- [x] **步骤 1：编写失败测试。** test_openai_adapter：MockTransport 检查请求体并断言纯文本、工具调用 ID/名称/参数映射。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_openai_adapter.py`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 通过 AsyncOpenAI.chat.completions.create 调用；不向测试发送真实网络请求。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests/test_openai_adapter.py`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：保存可独立检查的结果。** 本任务源码与测试已纳入本章阶段提交。

### 任务 3：示例与累计验证

**文件：** 新建 examples/model_demo.py；修改 README.md、PLAN.md。

**接口：** 示例仅用 FakeChatModel 展示模型响应，无需凭据。

- [x] **步骤 1：编写失败测试。** 运行示例与全量 tests，累计 15 个测试通过。
- [x] **步骤 2：确认测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests`，失败原因对应本任务缺失接口或行为。
- [x] **步骤 3：实现最小功能。** 记录已测与暂缓的适配行为；已在阶段 2 分支提交并推送。
- [x] **步骤 4：再次验证。** 运行 `.\.conda\python.exe -m pytest -q tests`；本章最后运行 `.\.conda\python.exe -m pytest -q tests`。
- [x] **步骤 5：提交阶段结果。** 已提交并推送 `codex/stage-2-model-abstraction`，提交 `6e95bc1`。

## 章末验收与暂缓

- 已验证：本章示例与累计测试通过；导入来自 `D:\code\agentscopeNew`。
- 暂缓：与本阶段无关的工具执行、流式事件、权限、服务及外部基础设施按 `PLAN.md` 的后续章节推进。
- 自查：本计划的接口、测试、文件范围与阶段 2 已实现代码一致；保持已完成标记，不把历史任务重新列为待办。
