# 阶段 14：远程沙箱实施计划

> **供执行本计划的 Agent 使用：** 按 `writing-plans` 逐任务执行并勾选；实施时使用 `superpowers:executing-plans`。除非用户要求，不派发子 Agent。

**目标：** 让本地工作空间的同一组工具用例在一个远程沙箱后端运行，并验证创建、执行、超时和清理。

**架构：** 保持 WorkspaceBase 文件/命令接口，新增后端生命周期 create/connect/close；先以可在本机运行的 Docker 后端作为共享契约样本，再按需接 E2B、Daytona、K8s。每个后端适配器独立，不污染 Agent 工具逻辑。

**技术栈：** Python 3.11、Docker SDK 或 CLI、pytest、可选 E2B/Daytona/K8s SDK。

**规格：** `PLAN.md` 阶段 14、`BASELINE.md`。固定参考提交的入口：`src/agentscope/workspace/_sandboxed_base.py`、`src/agentscope/workspace/_docker/_docker_backend.py`、`src/agentscope/workspace/_docker/_docker_workspace.py`、`src/agentscope/workspace/_e2b/_e2b_backend.py`、`src/agentscope/workspace/_daytona/_daytona_backend.py`、`src/agentscope/workspace/_k8s/_k8s_backend.py`、`tests/workspace_docker_test.py`。

## 全局约束

- 从上一章分支拉取 `codex/stage-14-remote-sandbox`；每项完成后提交，整章完成后推送。
- 使用独立环境 `.\.conda\python.exe`，确认 `agentscope.__file__` 指向本仓库。
- 固定参考提交 `5ff52f877de12d66a30d55af279dd4f42b1590f3`；迁入代码保留许可与署名。
- 离线单元测试用 Fake backend，不要求 Docker daemon；集成测试需显式标记。
- 远程工作空间生命周期必须可重复关闭，失败时也尝试清理。
- 用户或会话的工作空间隔离，容器内权限及资源限制需明确。
- 服务器部署配置和凭据不写入 Git；阿里云部署另行验收。

## 复核重点

1. 创建失败不会留下半初始化会话。
2. 命令超时后容器进程被终止。
3. 工作空间外路径仍无法读写。
4. close 调用两次仍安全。
5. 不同会话不能复用对方容器或文件。

---

### 任务 1：沙箱通用契约

**文件：** 新建 src/agentscope/workspace/_sandboxed_base.py；测试 tests/test_sandbox_contract.py。

**接口：** SandboxedWorkspace(WorkspaceBase)；create()、execute(command, timeout) -> ExecResult、close()。

- [ ] **步骤 1：写失败测试。** test_fake_backend_lifecycle：create、write/read、execute、close 顺序正确；重复 close 安全；创建失败时资源释放。 测试写入 `tests/test_sandbox_contract.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_sandbox_contract.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 复用阶段 8 的路径与文件操作语义，定义统一结果/异常。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_sandbox_contract.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage14): 沙箱通用契约` 作为提交信息；最后推送 `codex/stage-14-remote-sandbox`。

### 任务 2：Docker 后端

**文件：** 新建 src/agentscope/workspace/_docker/_docker_backend.py、_docker_workspace.py、__init__.py；测试 tests/test_workspace_docker.py。

**接口：** DockerWorkspace(image, limits, root) 满足 SandboxedWorkspace；后端负责容器创建、执行、复制和删除。

- [ ] **步骤 1：写失败测试。** test_docker_parity：带 docker 标记的集成测试在容器中执行阶段 8 文件/命令用例；超时、退出码和清理均有断言。 测试写入 `tests/test_workspace_docker.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_docker.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 为镜像、内存、CPU、网络和挂载声明默认值；Docker 不可用时集成测试明确跳过。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_docker.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage14): Docker 后端` 作为提交信息；最后推送 `codex/stage-14-remote-sandbox`。

### 任务 3：远程适配器样板

**文件：** 新建 src/agentscope/workspace/_e2b/_e2b_backend.py、_e2b_workspace.py；测试 tests/test_workspace_e2b.py。

**接口：** E2BWorkspace 使用同一 WorkspaceBase 契约，凭据从环境读取；连接失败返回后端错误。

- [ ] **步骤 1：写失败测试。** test_e2b_mock：Mock SDK 调用验证创建、读写、执行和关闭；真实 E2B 集成测试仅在显式环境标记运行。 测试写入 `tests/test_workspace_e2b.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_e2b.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 先实现一个云端后端；Daytona、K8s 按相同契约逐个迁入，不在本任务批量接全。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_workspace_e2b.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage14): 远程适配器样板` 作为提交信息；最后推送 `codex/stage-14-remote-sandbox`。

### 任务 4：示例、部署边界与回归

**文件：** 新建 examples/sandbox_demo.py、tests/test_sandbox_demo.py；修改 README.md、PLAN.md、pyproject.toml。

**接口：** 示例可选 local/docker，默认 local 不要求服务。

- [ ] **步骤 1：写失败测试。** test_sandbox_demo：默认示例离线退出码 0；Fake 契约及全量 tests 通过；启用 Docker 时集成测试通过。 测试写入 `tests/test_sandbox_demo.py`。
- [ ] **步骤 2：确认失败原因。** 运行 `.\.conda\python.exe -m pytest -q tests/test_sandbox_demo.py`；预期因本任务接口或行为缺失而失败。
- [ ] **步骤 3：实现最小功能。** 记录阿里云部署所需容器运行时、资源和清理策略；提交并推送。
- [ ] **步骤 4：运行验证。** 再运行 `.\.conda\python.exe -m pytest -q tests/test_sandbox_demo.py`，预期通过；本章末还运行 `.\.conda\python.exe -m pytest -q tests`、示例与 `.\.conda\python.exe -m pip check`。
- [ ] **步骤 5：提交。** 只暂存本任务所列文件，使用 `feat(stage14): 示例、部署边界与回归` 作为提交信息；最后推送 `codex/stage-14-remote-sandbox`。

## 章末验收与暂缓

- 验收：本章示例和分支目标可复现；成功、失败、恢复路径有测试；累计回归通过，README 记录调用链与固定参考版本的差异。
- 暂缓：本章未列出的平台/适配器/外部集成继续保留在 `PLAN.md`，不把它们视作已完成。
- 自查：逐条对应 `PLAN.md` 阶段 14；复核文件职责、接口名、五项风险和测试断言。若与参考接口不符，先修订本计划，再实施。
