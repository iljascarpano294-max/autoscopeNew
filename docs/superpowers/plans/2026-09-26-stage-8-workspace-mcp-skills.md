# 阶段 8：工作空间、MCP 与 Skill实施计划

> **供执行本计划的 Agent 使用：** 依照 `writing-plans` 的要求，逐任务执行并勾选。执行时使用 `superpowers:executing-plans`；本仓库由当前 Agent 原生实施，除非用户另行要求，不派发子 Agent。

**目标：** 在受控本地工作空间运行文件和命令工具，并分别验证一个 MCP 工具与一个本地 Skill 的最小用例。

**架构：** 先定义 WorkspaceBase/LocalWorkspace 的路径边界，再接内置 Read/Write/Edit/Glob/Grep 与受限命令；MCPClient 和 LocalSkillLoader 作为 Toolkit 的两个接入层。远程沙箱另设阶段。

**技术栈：** Python 3.11、pathlib、pytest、MCP SDK（只在本章引入）。

**规格：** 根目录 `PLAN.md` 的阶段 8；固定参考版本见 `BASELINE.md`。参考入口：`src/agentscope/workspace/_base.py`、`src/agentscope/workspace/_local_workspace.py`、`src/agentscope/tool/_builtin/_read.py`、`src/agentscope/tool/_builtin/_write.py`、`src/agentscope/mcp/_mcp_client.py`、`src/agentscope/skill/_local_loader.py`、`tests/workspace_local_test.py`、`tests/skill_loader_test.py`。

## 全局约束

- 每章从上一阶段分支创建 `codex/stage-8-workspace-mcp-skills`，保持前一阶段测试通过；计划文件先提交到规划分支，实施时随阶段分支继承。
- 运行命令使用 `.\.conda\python.exe`；验证 `agentscope.__file__` 位于 `D:\code\agentscopeNew`。
- 参考仓库固定提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入源码保留许可与署名。
- 所有文件工具仅操作测试或显式指定的工作空间根目录。
- 测试使用临时目录、本地 MCP server/Mock，不依赖云端服务。
- 命令工具需有超时、工作目录与输出上限；不能绕过阶段 6 权限决策。
- Skill 文本是外部数据，读取它不改变仓库 AGENTS.md 的优先级。

## 复核重点

1. ../ 路径和绝对路径逃逸被拒绝。
2. 符号链接指向根目录外时拒绝读写。
3. 不存在的文件、编码错误与命令超时返回结构化失败。
4. MCP 断线不会悄悄重复执行非幂等工具。
5. 恶意 Skill 路径不能读出其他目录文件。

---

### 任务 1：本地工作空间边界

**文件：** 新建 src/agentscope/workspace/_base.py、_local_workspace.py、__init__.py；测试 tests/test_workspace_local.py。

**接口：** WorkspaceBase.root；LocalWorkspace(root: Path)；resolve_path(path: str) -> Path；read/write 方法按参考抽象对齐。

- [ ] **步骤 1：写失败测试。** `test_workspace_boundary`：普通相对路径可读写；../、根外绝对路径、根外符号链接均被拒绝。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_local.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 先解析真实路径再验证根目录归属，统一路径异常。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_local.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage8): 本地工作空间边界`；每章完成后推送 `codex/stage-8-workspace-mcp-skills`。

### 任务 2：文件与命令工具

**文件：** 新建 src/agentscope/tool/_builtin/_read.py、_write.py、_edit.py、_glob.py、_grep.py、_bash.py；测试 tests/test_builtin_workspace_tools.py。

**接口：** Read/Write/Edit/Glob/Grep/Bash 均为 ToolBase 子类，接收 LocalWorkspace 并返回 ToolChunk。

- [ ] **步骤 1：写失败测试。** `test_file_round_trip`：写入、读取、替换、搜索同一临时目录得到预期内容；test_bash_timeout 断言超时不会挂起。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_builtin_workspace_tools.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 逐个接入工作空间边界与参数 schema；Bash 使用子进程超时和输出长度限制。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_builtin_workspace_tools.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage8): 文件与命令工具`；每章完成后推送 `codex/stage-8-workspace-mcp-skills`。

### 任务 3：MCP 接入

**文件：** 新建 src/agentscope/mcp/_config.py、_mcp_client.py、__init__.py；修改 src/agentscope/tool/_toolkit.py；测试 tests/test_mcp_local.py。

**接口：** MCPClient 配置本地 server，connect/list_tools/call_tool/close；Toolkit 注册 MCP 工具 schema。

- [ ] **步骤 1：写失败测试。** `test_local_mcp`：Mock server 暴露 echo，Toolkit 发现并调用；连接中断返回失败，关闭释放会话。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_mcp_local.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 先实现本地 stdio 方式与生命周期；远程 HTTP、重连策略后续按参考补齐。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_mcp_local.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage8): MCP 接入`；每章完成后推送 `codex/stage-8-workspace-mcp-skills`。

### 任务 4：本地 Skill 与验收

**文件：** 新建 src/agentscope/skill/_base.py、_local_loader.py、__init__.py；新建 examples/workspace_demo.py、tests/test_skill_local.py；修改 README.md、PLAN.md。

**接口：** LocalSkillLoader(directory).load() -> list[Skill]；Skill 包含 name、description、dir。

- [ ] **步骤 1：写失败测试。** `test_skill_loader`：有效 SKILL.md 被发现；路径逃逸/缺元数据被拒绝；示例和全量 tests 通过。 断言写在所列测试文件中。
- [ ] **步骤 2：验证测试先失败。** 运行 `.\.conda\python.exe -m pytest -q tests/test_skill_local.py`；预期因本任务接口尚未实现而失败，确认失败点与本任务相符。
- [ ] **步骤 3：实现最小功能。** 把 Skill 元数据接入 Toolkit 提示内容但不直接执行；提交并推送阶段分支。
- [ ] **步骤 4：验证转绿。** 运行 `.\.conda\python.exe -m pytest -q tests/test_skill_local.py`；预期通过。本章末另运行 `.\.conda\python.exe -m pytest -q tests` 和示例。
- [ ] **步骤 5：提交。** 只暂存本任务列出的源码、测试和文档，提交信息为 `feat(stage8): 本地 Skill 与验收`；每章完成后推送 `codex/stage-8-workspace-mcp-skills`。

## 章末验收与暂缓

- 验收：本章示例可离线运行，相关测试与累计回归通过；在 README 记录调用链、与固定参考提交的差异和测试结果。
- 暂缓：仅实现本章列出的纵向切片。完整提供商适配、外部基础设施和 其他未列出的后端 按 `PLAN.md` 的后续章节推进。
- 自查：逐项核对 `PLAN.md` 阶段 8 的验收、文件职责、接口名、上述五类失败输入及对应测试；若参考实现接口与计划不同，先更新本计划再实施。
