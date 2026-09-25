# 开发环境

本项目的 Conda 环境位于 `D:\code\agentscopeNew\.conda`，由参考项目的 `D:\code\agentscope\.conda` 克隆而来，Python 版本为 3.11.16。克隆后已移除指向参考项目的 `agentscope` 可编辑安装；本仓库尚未创建 Python 包，因此当前 `import agentscope` 不应成功。

## 已安装的依赖

- `requirements-all.txt`：从参考项目 `pyproject.toml` 的基础依赖和**所有**可选依赖组提取，包含开发与实时语音依赖；去除了 `agentscope[...]` 自引用。参考源码提交：`5ff52f8`。
- `requirements-lock-win-py311.txt`：本次在 Windows / Python 3.11 上实际安装的 pip 包版本，供复现和排查。Conda 的 Python 与底层库由 Conda 管理。
- `.conda/` 已加入 `.gitignore`，不会提交环境文件。

## 使用

在 PowerShell 中：

```powershell
conda activate D:\code\agentscopeNew\.conda
python --version
python -m pip check
```

不激活环境时也可以直接使用 `D:\code\agentscopeNew\.conda\python.exe`。

在另一台 Windows 机器上重建：先用 Conda 创建 Python 3.11.16 环境，再执行 `python -m pip install -r requirements-lock-win-py311.txt`。若希望按参考项目声明重新解析版本，改用 `requirements-all.txt`。

后续创建本项目的 `pyproject.toml` 和 `src/agentscope/` 后，在本环境中执行 `python -m pip install -e . --no-deps`，并检查 `agentscope.__file__` 指向 `agentscopeNew`。不要从本环境可编辑安装参考项目。

Web UI 的 Node/pnpm 依赖属于后续前端阶段，不在 Conda 环境中。Docker、Redis、数据库及外部 API 等服务也需要在对应阶段单独配置。
