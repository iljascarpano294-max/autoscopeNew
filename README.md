# AgentScope 渐进式重建

这是一个用于学习的 AgentScope 2.0 重建项目。参考仓库与固定提交见 [BASELINE.md](BASELINE.md)，阶段路线见 [PLAN.md](PLAN.md)。阶段 3 已建立可进行多轮文本对话的最小 Agent；版本标记仍为 `0.0.0`，表示尚未完成参考项目的功能。

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

## 阶段 3：最小 Agent

运行 `python examples/agent_demo.py` 可看到两轮离线对话。每次 `reply` 把新输入加入 `AgentState.context`，临时构造系统消息并附上历史，再调用模型；返回的 `ChatResponse` 转成 `AssistantMsg` 保存到上下文。系统消息不存入对话历史。

此阶段收到工具调用会明确报错，工具执行留给阶段 4。事件流、中断、权限、中间件和上下文压缩也未接入；相关测试只验证当前非流式文本闭环。
