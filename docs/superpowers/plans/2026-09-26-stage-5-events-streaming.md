# 阶段 5：事件与流式输出实施计划

> **供执行本计划的 Agent 使用：** 依照 `writing-plans` 的要求，逐任务执行并勾选。执行时使用 `superpowers:executing-plans`；本仓库由当前 Agent 原生实施，除非用户另行要求，不派发子 Agent。

**目标：** 让模型和 Agent 用事件流展示增量文本，同时保证最终消息与非流式语义一致。

**架构：** 先定义 reply/model/text/tool 事件，再实现事件聚合与 reply_stream。Fake 流式模型驱动确定性测试；console 仅负责渲染，不改变 Agent 状态。

**技术栈：** Python 3.11、Pydantic 2、asyncio、pytest。

**规格：** 根目录 `PLAN.md` 的阶段 5；固定参考版本见 `BASELINE.md`。参考入口：`src/agentscope/event/_event.py`、`src/agentscope/event/__init__.py`、`src/agentscope/console/_console.py`、`src/agentscope/console/_renderer.py`、`src/agentscope/model/_base.py`、`tests/event_test.py`、`tests/event_to_message_test.py`、`tests/console_test.py`。

## 全局约束

- 每章从上一阶段分支创建 `codex/stage-5-events-streaming`，保持前一阶段测试通过；计划文件先提交到规划分支，实施时随阶段分支继承。
- 运行命令使用 `.\.conda\python.exe`；验证 `agentscope.__file__` 位于 `D:\code\agentscopeNew`。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入源码保留许可与署名。
- 非流式 Agent.reply 继续可用；流式 reply_stream 返回 AgentEvent | Msg 的异步生成器。
- 事件内关联 reply_id、block_id 与顺序；最终 Msg 只产生一次。
- 本章只处理文本和已具备的工具结果；音频与实时传输留到阶段 15。
- 半途取消、模型异常和工具异常都必须产生可解释的结束状态。

## 复核重点

1. 空增量不会生成幽灵文本块。
2. 多块文本按 block_id 各自聚合，不串块。
3. 中途异常不应留下看似成功的 ReplyEndEvent。
4. 消费者提前关闭流时资源释放、状态可再次使用。
5. 流式结果与同输入非流式结果文本一致。

---

### 任务 1：事件模型与聚合

**文件：** 新建 src/agentscope/event/_event.py、__init__.py；测试 tests/test_event.py。

**接口：** ReplyStartEvent、ReplyEndEvent、ModelCallStartEvent、ModelCallEndEvent、TextBlockStartEvent、TextBlockDeltaEvent、TextBlockEndEvent；event_to_message(events) -> AssistantMsg。

- [ ] **步骤 1：写失败测试。** `test_event_order_and_merge`：start、两个 delta、end 产生一块完整文本；错序、重复 end、不同 block_id 混入分别断言明确错误。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_event.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 用带类型字段的 Pydantic 事件，聚合器按 reply_id/block_id 维护状态机，明确终止条件。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_event.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage5): 事件模型与聚合`；每章完成后推送 `codex/stage-5-events-streaming`。

### 任务 2：模型流式契约

**文件：** 修改 src/agentscope/model/_base.py、_fake.py、_model_response.py；测试 tests/test_model_stream.py。

**接口：** ChatModelBase.stream(messages, tools=None) -> AsyncGenerator[ChatResponse, None]；FakeChatModel 配置响应片段。

- [ ] **步骤 1：写失败测试。** `test_fake_stream`：预设两段文本，断言片段顺序、is_last 只在末段为真、调用记录一次；取消后不继续消耗响应。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_stream.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 扩展 Fake 模型并建立统一片段语义；真实 OpenAI 流式映射如依赖范围允许再接入，必须有无网络 MockTransport 测试。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_stream.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage5): 模型流式契约`；每章完成后推送 `codex/stage-5-events-streaming`。

### 任务 3：Agent 事件生产

**文件：** 修改 src/agentscope/agent/_agent.py；测试 tests/test_agent_stream.py。

**接口：** Agent.reply_stream(inputs) -> AsyncGenerator[AgentEvent | Msg, None]；Agent.reply 复用同一完成语义。

- [ ] **步骤 1：写失败测试。** `test_reply_stream`：断言 ReplyStart → ModelStart → TextStart/Delta/End → ModelEnd → ReplyEnd → 最终 Msg 的顺序及上下文只追加一次。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_stream.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 把模型片段转换为事件，聚合为最终消息；异常与取消走统一结束/清理路径。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_agent_stream.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage5): Agent 事件生产`；每章完成后推送 `codex/stage-5-events-streaming`。

### 任务 4：终端展示与回归

**文件：** 新建 src/agentscope/console/_console.py、_renderer.py、__init__.py；新建 examples/stream_demo.py、tests/test_console_stream.py；修改 README.md、PLAN.md。

**接口：** print_stream(events, file) -> None 只消费事件，不访问 Agent 内部状态。

- [ ] **步骤 1：写失败测试。** `test_console_stream`：捕获输出断言增量只打印一次且最终文本不重复；运行所有 tests。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_console_stream.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 提供终端示例与事件生命周期图；提交并推送阶段分支。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_console_stream.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage5): 终端展示与回归`；每章完成后推送 `codex/stage-5-events-streaming`。

## 章末验收与暂缓

- 验收：本章示例可离线运行，相关测试与累计回归通过；在 README 记录调用链、与固定参考提交的差异和测试结果。
- 暂缓：仅实现本章列出的纵向切片。完整提供商适配、外部基础设施及后续阶段能力 按 `PLAN.md` 的后续章节推进。
- 自查：逐项核对 `PLAN.md` 阶段 5 的验收、文件职责、接口名、上述五类失败输入及对应测试；若参考实现接口与计划不同，先更新本计划再实施。
