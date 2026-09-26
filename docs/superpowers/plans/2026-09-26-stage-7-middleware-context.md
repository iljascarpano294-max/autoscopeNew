# 阶段 7：中间件与上下文实施计划

> **供执行本计划的 Agent 使用：** 依照 `writing-plans` 的要求，逐任务执行并勾选。执行时使用 `superpowers:executing-plans`；本仓库由当前 Agent 原生实施，除非用户另行要求，不派发子 Agent。

**目标：** 为 Agent 生命周期加入可组合中间件，并实现一个可验证的预算和上下文压缩切片。

**架构：** MiddlewareBase 声明钩子，Agent 只在所需位置构造洋葱式调用链；system_prompt 使用顺序变换。预算与压缩作为独立中间件，不把策略硬编码进 Agent。

**技术栈：** Python 3.11、Pydantic 2、pytest、FakeChatModel。

**规格：** 根目录 `PLAN.md` 的阶段 7；固定参考版本见 `BASELINE.md`。参考入口：`src/agentscope/middleware/_base.py`、`src/agentscope/middleware/_budget.py`、`src/agentscope/agent/_agent.py`、`tests/middleware_test.py`、`tests/middleware_budget_test.py`、`tests/compress_context_test.py`。

## 全局约束

- 每章从上一阶段分支创建 `codex/stage-7-middleware-context`，保持前一阶段测试通过；计划文件先提交到规划分支，实施时随阶段分支继承。
- 运行命令使用 `.\.conda\python.exe`；验证 `agentscope.__file__` 位于 `D:\code\agentscopeNew`。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入源码保留许可与署名。
- 已完成的 reply/reply_stream/工具/权限行为在无中间件时不变。
- 调用链顺序固定：注册顺序进入，逆序退出；同一个 next_handler 最多执行一次。
- 中间件异常保留原异常并清理 Agent 运行状态。
- RAG、长期记忆与 tracing 分别留到阶段 13、16。

## 复核重点

1. 空中间件列表与未覆写钩子的行为一致。
2. 输入改写不会污染原消息对象。
3. 重复调用 next_handler 不得使工具或模型执行两次。
4. 预算耗尽时不再发起模型请求。
5. 压缩后系统消息与最近一轮对话不丢失。

---

### 任务 1：中间件协议和执行器

**文件：** 新建 src/agentscope/middleware/_base.py、__init__.py；测试 tests/test_middleware.py。

**接口：** MiddlewareBase.is_implemented(hook_name) -> bool；on_reply/on_reasoning/on_model_call/on_acting/on_system_prompt；compose_middlewares(...)。

- [ ] **步骤 1：写失败测试。** `test_onion_order`：A、B 两个中间件记录 A前/B前/模型/B后/A后；未实现钩子跳过；重复 next_handler 抛错。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_middleware.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 仅把阶段已有生命周期点接入 Agent，保留未来钩子的接口位置。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_middleware.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage7): 中间件协议和执行器`；每章完成后推送 `codex/stage-7-middleware-context`。

### 任务 2：预算限制

**文件：** 新建 src/agentscope/middleware/_budget.py；测试 tests/test_budget.py。

**接口：** BudgetMiddleware(max_model_calls: int)；在 on_model_call 中记录调用并阻断超额请求。

- [ ] **步骤 1：写失败测试。** `test_budget_stop`：max_model_calls=1 时第二次请求被拒绝，Fake 模型调用记录仍为 1；两个 Agent 的预算计数互不共享。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_budget.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 预算计数与一次回复或 Agent 生命周期的归属写清，避免全局可变状态。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_budget.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage7): 预算限制`；每章完成后推送 `codex/stage-7-middleware-context`。

### 任务 3：上下文压缩

**文件：** 修改 src/agentscope/state/_state.py、src/agentscope/agent/_agent.py；新建 src/agentscope/middleware/_context.py、tests/test_context_compression.py。

**接口：** ContextCompressionMiddleware(max_messages: int, keep_recent: int)；压缩后的 context 为 Msg 列表。

- [ ] **步骤 1：写失败测试。** `test_compress_context`：超过阈值后保留系统提示与最近两轮消息，旧消息变成一条摘要；低于阈值不改变上下文。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_context_compression.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 先用可注入摘要函数/Fake 模型验证数据流，真实总结模型后置；确保不会重复压缩同一批消息。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_context_compression.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage7): 上下文压缩`；每章完成后推送 `codex/stage-7-middleware-context`。

### 任务 4：示例和回归

**文件：** 新建 examples/middleware_demo.py；修改 README.md、PLAN.md；测试 tests/test_middleware_demo.py。

**接口：** 示例展示一个记录调用的自定义中间件与预算行为。

- [ ] **步骤 1：写失败测试。** `test_middleware_demo`：运行示例退出码 0、记录的钩子顺序正确；全量 tests 通过。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_middleware_demo.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 文档说明各钩子何时触发与暂缓范围；提交并推送阶段分支。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_middleware_demo.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage7): 示例和回归`；每章完成后推送 `codex/stage-7-middleware-context`。

## 章末验收与暂缓

- 验收：本章示例可离线运行，相关测试与累计回归通过；在 README 记录调用链、与固定参考提交的差异和测试结果。
- 暂缓：仅实现本章列出的纵向切片。完整提供商适配、外部基础设施及后续阶段能力 按 `PLAN.md` 的后续章节推进。
- 自查：逐项核对 `PLAN.md` 阶段 7 的验收、文件职责、接口名、上述五类失败输入及对应测试；若参考实现接口与计划不同，先更新本计划再实施。
