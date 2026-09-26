# 阶段 16：可观测性与整体对齐实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 逐任务执行并勾选；实施时使用 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 让一次 Agent 调用能追踪到模型与工具步骤，并按模块核对新项目与固定参考版本的公开接口和测试覆盖。

**架构：** TracingMiddleware 在生命周期钩子创建 span，结构化日志与指标使用同一关联 ID；对齐清单逐模块比较导出名、方法签名和行为测试。提供商适配器按独立小批次补齐，并记录尚未完成的外部集成。

**技术栈：** Python 3.11、OpenTelemetry、pytest、ruff/mypy（按参考配置）。

**规格：** `PLAN.md` 阶段 16、`BASELINE.md`。固定参考提交的入口：`src/agentscope/middleware/_tracing/_setup.py`、`src/agentscope/middleware/_tracing/_trace.py`、`src/agentscope/middleware/_tracing/_attributes.py`、`src/agentscope/model/_deepseek`、`src/agentscope/model/_dashscope`、`src/agentscope/model/_gemini`、`tests/tracing_test.py`、`tests/model_deepseek_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-16-observability-alignment`；每项完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- Trace 中不得记录 API Key、服务器密码或敏感工具参数。
- 无 tracing 配置时 Agent 行为和性能开销应接近原状态。
- 对齐以固定提交为准，明确标注新项目暂缺功能而不宣称完全等价。
- 各提供商 Mock 测试离线运行，真实 API 只做可选手动验收。

## 复核重点

1. 异常模型调用仍形成闭合 span。
2. 工具失败 span 保留状态但不泄露输入秘密。
3. 同一请求内 span 父子关系稳定。
4. 公开接口差异可被清单/脚本发现。
5. 新适配器缺少凭据时不在 import 阶段报错。

---

### 任务 1：追踪生命周期

**文件：** 新建 src/agentscope/middleware/_tracing/_setup.py、_trace.py、_attributes.py、__init__.py；测试 tests/test_tracing.py。

**接口：** setup_tracing(exporter=None)；TracingMiddleware 在 reply/model/tool 钩子中生成关联 span。

- [ ] **步骤 1：写失败测试。** test_trace_tree：一次工具回合形成 reply → model/tool/model 的父子链；失败路径 span 关闭并标记错误。 测试写入 `tests/test_tracing.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_tracing.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 在原有 middleware 钩子挂 span，使用可注入内存 exporter 进行离线测试。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_tracing.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage16): 追踪生命周期` 作为提交信息；最后推送 `codex/stage-16-observability-alignment`。

### 任务 2：日志、指标与脱敏

**文件：** 新建 src/agentscope/_logging.py；测试 tests/test_observability_redaction.py。

**接口：** 结构化日志包含 run_id、session_id、event_type；指标记录调用量、时延和失败数。

- [ ] **步骤 1：写失败测试。** test_secret_redaction：给定模拟 API Key 和工具敏感字段，日志与 span 字符串均不包含原值；无 exporter 时调用仍成功。 测试写入 `tests/test_observability_redaction.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_observability_redaction.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 集中定义允许采集的属性白名单与采样配置，不把消息全文默认上传。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_observability_redaction.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage16): 日志、指标与脱敏` 作为提交信息；最后推送 `codex/stage-16-observability-alignment`。

### 任务 3：提供商适配器分批对齐

**文件：** 新增 src/agentscope/model/_deepseek/、_dashscope/ 等需要的适配器与 formatter/credential；测试 tests/test_model_adapters.py。

**接口：** 各适配器遵循 ChatModelBase 的响应、工具调用、流式与 usage 语义；按固定参考公开名导出。

- [ ] **步骤 1：写失败测试。** test_adapter_contract：Mock transport 对每个已迁入适配器校验纯文本、工具调用、错误与 usage；无凭据 import 成功。 测试写入 `tests/test_model_adapters.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_model_adapters.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 按提供商一个适配器一提交，先 DeepSeek（与用户现有 Key 对应）再其他；每个适配器完成才加入公开导出。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_model_adapters.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage16): 提供商适配器分批对齐` 作为提交信息；最后推送 `codex/stage-16-observability-alignment`。

### 任务 4：接口差异审计与最终验收

**文件：** 新建 docs/compatibility-matrix.md、scripts/check_public_api.py、tests/test_public_api.py；修改 README.md、PLAN.md。

**接口：** 清单按模块列出：参考符号、目标符号、测试、状态（已对齐/部分/暂缓）；脚本比较 import 可见名称。

- [ ] **步骤 1：写失败测试。** test_public_api：已标记对齐的名称均可导入；脚本输出差异清单；全量 tests、pip check 和示例通过。 测试写入 `tests/test_public_api.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_public_api.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 将所有未覆盖服务/平台能力列入暂缓清单，保留后续扩展入口；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_public_api.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage16): 接口差异审计与最终验收` 作为提交信息；最后推送 `codex/stage-16-observability-alignment`。

## 章末验收与暂缓

- 验收：本章示例和分支目标可复现；成功、失败、恢复路径有测试；累计回归通过，README 记录调用链与固定参考版本的差异。
- 暂缓：本章未列出的平台/适配器/外部集成继续保留在 `PLAN.md`，不把它们视作已完成。
- 自查：逐条对应 `PLAN.md` 阶段 16；复核文件职责、接口名、五项风险和测试断言。若与参考接口不符，先修订本计划，再实施。
