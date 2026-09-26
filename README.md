# AgentScope 渐进式重建

这是一个用于学习的 AgentScope 2.0 重建项目。参考仓库与固定提交见 [BASELINE.md](BASELINE.md)，阶段路线见 [PLAN.md](PLAN.md)。当前只完成**阶段 0：固定基线与 Python 包骨架**，版本标记为 `0.0.0`。

## 运行阶段 0

使用已经建立的 Conda 环境，在本目录执行：

```powershell
.\.conda\python.exe -m pip install -e . --no-deps
.\.conda\python.exe examples\smoke_import.py
.\.conda\python.exe -m pytest -q tests
.\.conda\python.exe -m pip check
```

示例应打印 `D:\code\agentscopeNew\src\agentscope\__init__.py`，以确认没有意外导入参考仓库。独立环境和完整依赖清单见 [ENVIRONMENT.md](ENVIRONMENT.md)。

阶段 1 将开始构建消息与模型响应数据结构；本阶段没有 Agent 对话或工具调用功能。
