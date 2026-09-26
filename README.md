# AgentScope 渐进式重建

这是一个用于学习的 AgentScope 2.0 重建项目。参考仓库与固定提交见 [BASELINE.md](BASELINE.md)，阶段路线见 [PLAN.md](PLAN.md)。阶段 2 已建立模型抽象、离线 Fake 模型和一个 OpenAI Chat Completions 适配器；版本标记仍为 `0.0.0`，表示尚未完成参考项目的功能。

## 运行阶段 0

使用已经建立的 Conda 环境，在本目录执行：

```powershell
.\.conda\python.exe -m pip install -e . --no-deps
.\.conda\python.exe examples\smoke_import.py
.\.conda\python.exe -m pytest -q tests
.\.conda\python.exe -m pip check
```

示例应打印 `D:\code\agentscopeNew\src\agentscope\__init__.py`，以确认没有意外导入参考仓库。独立环境和完整依赖清单见 [ENVIRONMENT.md](ENVIRONMENT.md)。

## 阶段 1：消息与响应

运行 `python examples/message_demo.py` 可查看 `UserMsg`、助手的工具调用块和 `ChatResponse` 的数据形态。`Msg` 持有角色、内容块、ID 和元数据；`ChatResponse` 持有模型返回的内容及结束标记。对应测试为 `tests/test_message.py` 与 `tests/test_model_response.py`。

这一步只存储工具调用的数据，不执行工具。参考实现中的事件应用、权限规则和流式音频块将在后续阶段补齐。

## 阶段 2：模型抽象

运行 `python examples/model_demo.py` 可用 Fake 模型生成文本和工具调用数据。`ChatModelBase` 负责有限重试和取消处理，具体模型负责 `_call_api`。OpenAI 适配器已用 `httpx.MockTransport` 验证消息格式和文本/工具调用映射，不需要真实 API Key 或网络。

此阶段仅实现非流式 Chat Completions 路径。流式输出、结构化输出、模型卡片以及其他模型厂商将在后续阶段扩展。
