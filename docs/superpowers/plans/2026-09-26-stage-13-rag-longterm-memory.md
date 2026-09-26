# 阶段 13：RAG 与长期记忆实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 逐任务执行并勾选；实施时使用 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 用一份文档完成解析、切块、索引、检索与引用，并跨会话写入和召回一条长期记忆。

**架构：** 文档处理层将来源、片段和引用分离；先用进程内/本地向量索引与 Fake embedding 验证链路，再接参考向量库和记忆中间件。长记忆只通过中间件注入，不让 Agent 直接依赖数据库。

**技术栈：** Python 3.11、Pydantic 2、pytest、向量存储适配器。

**规格：** `PLAN.md` 阶段 13、`BASELINE.md`。固定参考提交的入口：`src/agentscope/rag/_document.py`、`src/agentscope/rag/_knowledge.py`、`src/agentscope/rag/_parser/_text.py`、`src/agentscope/rag/_chunker/_approx_token_chunker.py`、`src/agentscope/rag/_vdb/_vector_store.py`、`src/agentscope/middleware/_rag.py`、`src/agentscope/middleware/_longterm_memory/_mem0/_middleware.py`、`src/agentscope/middleware/_longterm_memory/_reme/_middleware.py`、`tests/rag_parser_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-13-rag-longterm-memory`；每项完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- 最小示例仅需本地文本文件与 Fake embedding，无外部 API。
- 检索结果保留文档 ID、片段 ID、原始来源和可展示的引用。
- 重复导入同一版本文档不能产生重复索引记录。
- Mem0/ReMe 作为可选适配器；未配置时不影响普通 Agent。

## 复核重点

1. 空文档不产生无意义向量。
2. 重复导入和删除后检索结果正确。
3. 检索不相关文档时不伪造引用。
4. 两个用户或会话的私有记忆不串用。
5. 向量维度改变时明确拒绝或重建索引。

---

### 任务 1：文档解析与切块

**文件：** 新建 src/agentscope/rag/_document.py、_parser/_text.py、_chunker/_approx_token_chunker.py、各级 __init__.py；测试 tests/test_rag_document.py。

**接口：** Document(id, source, text)；TextParser.parse(path) -> Document；ApproxTokenChunker.split(document) -> list[Chunk]。

- [ ] **步骤 1：写失败测试。** test_parse_and_chunk：UTF-8 文本解析后来源不丢；给定短文本得到有序片段和稳定 offset；空文档得到空列表。 测试写入 `tests/test_rag_document.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_rag_document.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 先实现纯文本路径，PDF/Office/图片解析留作同章后续可选适配器。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_rag_document.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage13): 文档解析与切块` 作为提交信息；最后推送 `codex/stage-13-rag-longterm-memory`。

### 任务 2：索引与检索

**文件：** 新建 src/agentscope/rag/_vdb/_vector_store.py、_knowledge.py；测试 tests/test_rag_retrieval.py。

**接口：** VectorStore.upsert/delete/search；KnowledgeBase.add_document/delete_document/retrieve(query, top_k) -> list[RetrievedChunk]。

- [ ] **步骤 1：写失败测试。** test_retrieve_citation：预设向量让相关片段排名第一，返回 source 和 chunk_id；重复 upsert 不增记录；删除后检索为空。 测试写入 `tests/test_rag_retrieval.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_rag_retrieval.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 用 Fake embedding 驱动本地索引，定义维度检查与幂等键；随后可接参考 Qdrant/Milvus Lite 等。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_rag_retrieval.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage13): 索引与检索` 作为提交信息；最后推送 `codex/stage-13-rag-longterm-memory`。

### 任务 3：RAG 注入与回答

**文件：** 新建 src/agentscope/middleware/_rag.py；测试 tests/test_rag_middleware.py。

**接口：** RAGMiddleware(knowledge_base, top_k) 在模型调用前注入检索片段，输出保留引用元数据。

- [ ] **步骤 1：写失败测试。** test_rag_answer：Fake 模型收到检索片段与来源；无结果时不添加伪上下文；引用与最终回答的来源一致。 测试写入 `tests/test_rag_middleware.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_rag_middleware.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 检索内容作为外部数据处理，限制长度并保持原用户消息。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_rag_middleware.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage13): RAG 注入与回答` 作为提交信息；最后推送 `codex/stage-13-rag-longterm-memory`。

### 任务 4：跨会话记忆和示例

**文件：** 新建 src/agentscope/middleware/_longterm_memory/_mem0/_middleware.py、examples/rag_demo.py、tests/test_longterm_memory.py；修改 README.md、PLAN.md。

**接口：** LongTermMemoryMiddleware.save(user_id, fact)、recall(user_id, query)；可由其他适配器替换。

- [ ] **步骤 1：写失败测试。** test_memory_isolation：用户 A 会话 1 写入后会话 2 可召回，用户 B 不可召回；示例与全量 tests 通过。 测试写入 `tests/test_longterm_memory.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_longterm_memory.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 先做本地存储切片，再按参考增加 Mem0/ReMe 适配；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_longterm_memory.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage13): 跨会话记忆和示例` 作为提交信息；最后推送 `codex/stage-13-rag-longterm-memory`。

## 章末验收与暂缓

- 验收：本章示例和分支目标可复现；成功、失败、恢复路径有测试；累计回归通过，README 记录调用链与固定参考版本的差异。
- 暂缓：本章未列出的平台/适配器/外部集成继续保留在 `PLAN.md`，不把它们视作已完成。
- 自查：逐条对应 `PLAN.md` 阶段 13；复核文件职责、接口名、五项风险和测试断言。若与参考接口不符，先修订本计划，再实施。
