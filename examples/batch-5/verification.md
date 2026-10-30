# 业务结果与引用校验验证

86项离线测试通过。受控Mock验证五类状态、混合分项优先级、引用标记与本轮read-set、逐字原文回填、资料缺口及中断证据保留。

曾发现测试未真正发送非法状态，以及安装包未重装时可能复用旧构建；修正测试输入并重装后复跑。输出中的材料、期限双方与产品事实均与对应片段核对；这证明工程校验，不证明真实模型语义决策。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 记录 | 实际结果 | 检查 |
| --- | --- | --- |
| [正常结束](answered.json) | answered | 该次原文读取后回填引用 |
| [材料+冲突](needs_clarification.json) | needs_clarification | 保留材料和期限双方引用、缺口及单个依据请求 |
| [材料+资料缺失](insufficient_evidence.json) | insufficient_evidence | 保留材料，不把资料缺失写成事实不存在 |
| [材料+天气](out_of_scope.json) | out_of_scope | 保留材料及天气边界 |
| [执行中断](interrupted.json) | incomplete | 已读证据保留，执行问题单列，不追加模型收尾 |

## 原始证据

- [完整报告](offline-tests.txt)
- [正常结束](answered.json)
- [材料+冲突](needs_clarification.json)
- [材料+资料缺失](insufficient_evidence.json)
- [材料+天气](out_of_scope.json)
- [执行中断](interrupted.json)
- [expectations.json](expectations.json)
- [source-fingerprints.json](source-fingerprints.json)
