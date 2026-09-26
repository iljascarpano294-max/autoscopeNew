# 阶段 0：固定基线与项目骨架实施计划

> **供执行本计划的 Agent 使用：** 本章已由当前 Agent 原生执行。按 `writing-plans` 格式保留任务和已完成状态；后续复核可逐项重跑验证。

**目标：** 固定参考仓库版本，建立可安装、可测试、可独立运行的 AgentScope 学习骨架。

**架构：** 新仓库使用 `src/agentscope` 布局和独立 Conda 环境。骨架只包含包入口、烟雾测试及示例，不迁入业务功能；参考提交和工作区例外写入 BASELINE.md。

**技术栈：** Python 3.11、setuptools、pytest、Conda。

**规格：** `PLAN.md` 阶段 0、`BASELINE.md`、`ENVIRONMENT.md`。

## 全局约束

- 包名保持 `agentscope`，版本 `0.0.0`；不宣称已经实现参考仓库 `2.0.8` 的能力。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；原工作区未提交改动不计入基线。
- 新旧仓库使用不同 Conda 环境；验证导入源必须是 `D:\code\agentscopeNew`。
- 虚拟环境、密钥、缓存均不得加入 Git。

## 复核重点

1. 可编辑安装后导入来源是新仓库。
2. 参考提交记录为完整 SHA，不随参考仓库 HEAD 漂移。
3. `.conda` 及凭据文件不被 Git 跟踪。
4. 新包在没有业务模块时仍可安装和导入。
5. 烟雾测试在独立环境下通过。

---

### 任务 1：记录基线和仓库边界

**文件：** 新建 `BASELINE.md`、`AGENTS.md`；修改 `PLAN.md`。

**接口：** 文档写明固定 SHA、参考路径、新仓库路径和工作区例外。

- [x] **步骤 1：写检查项。** 比较 `git -C D:\code\agentscope rev-parse HEAD` 与固定 SHA；确认原仓库未提交变更仅是已记录的 `.gitignore` 和 `docs/architecture_analysis/`。
- [x] **步骤 2：核对原始状态。** 查看 `git status --short` 与参考提交，保证记录对应实际输入。
- [x] **步骤 3：写入文档。** 将定位、参考边界、阶段验收和协作约定写清。
- [x] **步骤 4：验证。** 检查基线文档中的完整 SHA 和工作区例外。
- [x] **步骤 5：保存。** 文件已纳入阶段 0 提交。

### 任务 2：建立可安装的包和独立环境

**文件：** 新建 `pyproject.toml`、`src/agentscope/__init__.py`、`ENVIRONMENT.md`、`requirements-all.txt`、`requirements-lock-win-py311.txt`；修改 `.gitignore`。

**接口：** `import agentscope` 成功，`agentscope.__file__` 指向新仓库；环境 Python 3.11.16。

- [x] **步骤 1：写烟雾测试。** 在 `tests/test_package.py` 断言可导入包且导入路径位于 `agentscopeNew`。
- [x] **步骤 2：确认测试先失败。** 在安装骨架前运行测试，确认因包不可导入或路径不对而失败。
- [x] **步骤 3：实现最小骨架。** 配置 `src` 布局、包版本和可编辑安装；建立独立 Conda 环境并记录依赖。
- [x] **步骤 4：运行验证。** `.\.conda\python.exe -m pip install -e . --no-deps`、`.\.conda\python.exe -m pytest -q tests`、`.\.conda\python.exe -m pip check`。
- [x] **步骤 5：保存。** 骨架和环境说明已纳入阶段 0 提交，`.conda` 被忽略。

### 任务 3：运行示例和提交阶段结果

**文件：** 新建 `examples/smoke_import.py`；修改 `README.md`。

**接口：** 示例打印当前环境导入的 `agentscope.__file__`。

- [x] **步骤 1：定义验收。** 示例退出码为 0，路径包含 `D:\code\agentscopeNew\src\agentscope`。
- [x] **步骤 2：运行示例。** `.\.conda\python.exe examples/smoke_import.py`。
- [x] **步骤 3：写运行说明。** README 记录安装、示例、测试和环境隔离命令。
- [x] **步骤 4：再次验证。** 阶段 0 的两个烟雾测试通过。
- [x] **步骤 5：提交并推送。** 已推送 `codex/stage-0-skeleton`，提交 `d3827a2`。

## 章末验收与暂缓

- 已验证：包可独立安装和导入，烟雾测试通过，固定基线及环境文档齐全。
- 暂缓：消息、模型、Agent、工具及所有服务能力由后续章节逐步实现。
- 自查：骨架没有批量复制参考项目源码，版本号准确表达当前学习状态。
