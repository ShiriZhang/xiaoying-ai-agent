# 模型循环、预算与故障验证

验证官方DeepSeek适配、单动作循环、工具观察回传、预算、一次故障恢复、一次格式修正、超时及Trace。真实协议冒烟使用实际read→finish；首次网络失败与成功复跑分别保存，不能当作六类完整业务验收。

工具失败和恢复均计数；第6工具后立即停止。最多7次模型请求可达，第8次不可达，依据见[预算说明](budget-decision.md)。超时停止等待但不能撤销底层请求或服务商计费；未知usage保持未知。

## 原始证据

- [budget-decision.md](budget-decision.md)
- [unittest.txt](unittest.txt)
- [fingerprints.json](fingerprints.json)
