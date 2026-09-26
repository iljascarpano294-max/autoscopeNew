# 阶段 11：持久化与分布式存储实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 的步骤逐任务勾选；实施方法为 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 让会话可在重启后恢复，并建立可替换的存储与消息总线接口。

**架构：** 先以 SQLite 实现 StorageBase 的会话和消息读写，用文件数据库模拟进程重建；再抽象 MessageBus 并实现进程内版本。Redis、SQL 服务和 S3 作为适配器逐一接入，只有配置时才要求外部服务。

**技术栈：** Python 3.11、SQLite/SQLAlchemy、Redis 客户端、pytest。

**规格：** `PLAN.md` 阶段 11、`BASELINE.md`。固定参考提交的入口：`src/agentscope/app/storage/_base.py`、`src/agentscope/app/storage/_sql/_storage.py`、`src/agentscope/app/storage/_redis_storage.py`、`src/agentscope/app/message_bus/_base.py`、`src/agentscope/app/message_bus/_in_memory_message_bus.py`、`src/agentscope/app/message_bus/_redis_message_bus.py`、`tests/storage_sql_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-11-storage-message-bus`；每项功能完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- 存储读取后恢复 AgentState，版本不兼容时返回明确错误。
- 数据库、Redis、S3 凭据只从环境变量/本机秘密来源读取。
- 重试不得造成重复消息或重复任务消费。
- 部署阿里云前先写资源清单和端口/认证配置，本次仅规划。

## 复核重点

1. 重启恢复后上下文顺序不变。
2. 写入失败不能留下半个消息记录。
3. 总线重复投递不得重复执行非幂等工具。
4. Redis 断线应暴露可重试错误。
5. 旧 schema/损坏状态读取时明确迁移或拒绝。

---

### 任务 1：存储契约与 SQLite

**文件：** 新建 src/agentscope/app/storage/_base.py、_sql/_storage.py、_sql/__init__.py；测试 tests/test_storage_sqlite.py。

**接口：** async StorageBase.save_session(record) -> None、async load_session(session_id) -> SessionRecord、async append_message(session_id, msg) -> None；SQLiteStorage(db_path)。

- [ ] **步骤 1：写失败测试。** test_restart_restore：第一实例写入两轮，关闭后第二实例加载顺序一致；事务失败时记录数不变。 测试写入 `tests/test_storage_sqlite.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_storage_sqlite.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 用事务存会话/消息并记录 schema 版本；执行时对齐固定参考接口后同步本计划。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_storage_sqlite.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage11): 存储契约与 SQLite` 作为提交信息；最后推送 `codex/stage-11-storage-message-bus`。

### 任务 2：聊天服务接入持久化

**文件：** 修改 src/agentscope/app/_service/_session.py、_chat.py；测试 tests/test_persisted_chat.py。

**接口：** SessionService 接收 StorageBase；ChatService 在成功完成一轮后保存状态。

- [ ] **步骤 1：写失败测试。** test_chat_after_restart：重建服务后同一会话继续对话，Fake 模型收到旧历史；损坏状态返回明确异常。 测试写入 `tests/test_persisted_chat.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_persisted_chat.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 只在模型与工具结果确定后提交状态，避免异常半轮写入。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_persisted_chat.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage11): 聊天服务接入持久化` 作为提交信息；最后推送 `codex/stage-11-storage-message-bus`。

### 任务 3：消息总线与去重

**文件：** 新建 src/agentscope/app/message_bus/_base.py、_in_memory_message_bus.py、__init__.py；测试 tests/test_message_bus.py。

**接口：** MessageBus.publish(topic, event_id, payload)、subscribe(topic)、ack(event_id)；InMemoryMessageBus。

- [ ] **步骤 1：写失败测试。** test_bus_delivery：同 event_id 重投只被处理一次；未 ack 事件可重试；不同 topic 隔离。 测试写入 `tests/test_message_bus.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_message_bus.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 定义事件 ID、确认和重放边界；先实现进程内语义。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_message_bus.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage11): 消息总线与去重` 作为提交信息；最后推送 `codex/stage-11-storage-message-bus`。

### 任务 4：可选外部后端与文档

**文件：** 新建 src/agentscope/app/message_bus/_redis_message_bus.py、src/agentscope/app/storage/_redis_storage.py、examples/storage_demo.py、tests/test_storage_adapters.py；修改 README.md、PLAN.md、pyproject.toml。

**接口：** RedisMessageBus 与 RedisStorage 通过环境配置创建；服务不可用时抛连接错误。

- [ ] **步骤 1：写失败测试。** test_external_config：缺配置时报可读错误；有服务时运行带标记集成测试；SQLite 示例与全量离线 tests 通过。 测试写入 `tests/test_storage_adapters.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_storage_adapters.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 记录 Redis/SQL/S3 的角色与可选性，S3 blob store 若本阶段接入则单独测试；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_storage_adapters.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage11): 可选外部后端与文档` 作为提交信息；最后推送 `codex/stage-11-storage-message-bus`。

## 章末验收与暂缓

- 验收：示例可按本章约束运行；计划内成功、错误和恢复路径可被测试；累计回归通过，README 记录数据流及固定参考版本的差异。
- 暂缓：本章未列出的适配器、频道或高级特性由 `PLAN.md` 的后续阶段处理。
- 自查：逐条对应 `PLAN.md` 阶段 11 的目标；复核文件职责、接口名称、五项风险和测试断言。若与参考接口不符，先修订本计划，再执行。
