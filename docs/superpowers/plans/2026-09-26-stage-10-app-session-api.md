# 阶段 10：应用服务与会话实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 的步骤逐任务勾选；实施方法为 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 提供进程内会话服务和 HTTP API，创建会话、接收消息并返回 Agent 回复。

**架构：** 应用层把 Agent 实例、会话记录和运行锁放在服务对象中；FastAPI 路由只验证输入与映射响应。依赖注入允许在测试中使用 Fake 模型，持久化留到阶段 11。

**技术栈：** Python 3.11、FastAPI、Pydantic 2、httpx、pytest。

**规格：** `PLAN.md` 阶段 10、`BASELINE.md`。固定参考提交的入口：`src/agentscope/app/_app.py`、`src/agentscope/app/_lifespan.py`、`src/agentscope/app/_service/_session.py`、`src/agentscope/app/_service/_chat.py`、`src/agentscope/app/_router/_session.py`、`src/agentscope/app/_router/_chat.py`、`tests/test_e2e_api.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-10-app-session-api`；每项功能完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- API 输入输出有明确 schema，错误不泄露堆栈或凭据。
- 一个 session_id 的并发请求串行化；不同会话独立。
- 阶段 10 使用进程内存储，重启后会话消失并返回未找到。
- 不得把真实 DeepSeek Key 写入测试、文档或响应。

## 复核重点

1. 未知会话 ID 返回 404。
2. 空消息或非法 payload 返回 422。
3. 同会话并发回复不乱序。
4. 模型异常返回结构化错误且不产生伪助手消息。
5. 关闭应用后后台任务与会话资源释放。

---

### 任务 1：会话记录与服务

**文件：** 新建 src/agentscope/app/_service/_session.py、_service/__init__.py；测试 tests/test_session_service.py。

**接口：** SessionService.create(agent_id) -> SessionRecord；get(session_id) -> SessionRecord；delete(session_id) -> None。

- [ ] **步骤 1：写失败测试。** test_session_lifecycle：创建得到唯一 ID，读取相同记录，删除后 get 抛未找到；两个会话状态不共享。 测试写入 `tests/test_session_service.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_session_service.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 用进程内字典保存会话元数据与 AgentState，明确 ID 和时间字段。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_session_service.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage10): 会话记录与服务` 作为提交信息；最后推送 `codex/stage-10-app-session-api`。

### 任务 2：聊天服务与串行化

**文件：** 新建 src/agentscope/app/_service/_chat.py；测试 tests/test_chat_service.py。

**接口：** async ChatService.send(session_id: str, message: str) -> AssistantMsg；依赖 SessionService 与 Agent 工厂。

- [ ] **步骤 1：写失败测试。** test_chat_turns：同会话两轮模型收到有序历史；并发输入按锁获取顺序串行；模型异常不附加伪回复。 测试写入 `tests/test_chat_service.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_chat_service.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 为每个会话保存独立锁，调用既有 Agent.reply，不在服务层重复实现工具循环。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_chat_service.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage10): 聊天服务与串行化` 作为提交信息；最后推送 `codex/stage-10-app-session-api`。

### 任务 3：HTTP 路由与生命周期

**文件：** 新建 src/agentscope/app/_app.py、_lifespan.py、_router/_session.py、_router/_chat.py、_router/_schema/_session.py、_router/_schema/_chat.py；测试 tests/test_app_api.py。

**接口：** create_app(agent_factory) -> FastAPI；POST /sessions、POST /sessions/{session_id}/messages、GET /sessions/{session_id}。

- [ ] **步骤 1：写失败测试。** test_api_roundtrip：ASGI 客户端创建会话并发消息得 200；未知会话 404；空消息 422；响应不含内部凭据。 测试写入 `tests/test_app_api.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_app_api.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** FastAPI 依赖注入服务和请求模型；统一映射领域错误到 HTTP 状态。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_app_api.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage10): HTTP 路由与生命周期` 作为提交信息；最后推送 `codex/stage-10-app-session-api`。

### 任务 4：演示和回归

**文件：** 新建 examples/app_demo.py、tests/test_app_demo.py；修改 README.md、PLAN.md、pyproject.toml。

**接口：** 示例在本地启动 ASGI 应用并通过 httpx 测一轮，无公网依赖。

- [ ] **步骤 1：写失败测试。** test_app_demo：运行示例退出码 0；应用关闭后资源释放；全量 tests 通过。 测试写入 `tests/test_app_demo.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_app_demo.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 记录启动和 API 请求方式，标明进程内会话重启丢失；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_app_demo.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage10): 演示和回归` 作为提交信息；最后推送 `codex/stage-10-app-session-api`。

## 章末验收与暂缓

- 验收：示例可按本章约束运行；计划内成功、错误和恢复路径可被测试；累计回归通过，README 记录数据流及固定参考版本的差异。
- 暂缓：本章未列出的适配器、频道或高级特性由 `PLAN.md` 的后续阶段处理。
- 自查：逐条对应 `PLAN.md` 阶段 10 的目标；复核文件职责、接口名称、五项风险和测试断言。若与参考接口不符，先修订本计划，再执行。
