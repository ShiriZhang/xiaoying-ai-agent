# 真实模型服务中断记录

真实回归因HTTP402中断时，最终业务源码仅31/40轮有实际记录，不能判定完整通过。未完成索引为evidence-index-incomplete.json，记录passed=false；2次失败请求usage未知。

此快照仅用于保留服务失败和验证不足，之后在新目录补齐40轮，见[完整回归](verification.md)。下列原始证据中的final目录和费用对应中断前或更早版本，不能替代resumed与validated最终组。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 最终组 | 轮数 | 实际证据 |
| --- | ---: | --- |
| 核心六类各两次 | 18 | [core-final](runs/core-final/summary.json)，含住房补贴、天气、完整两轮与临时/持续read故障 |
| 规则与部分结果 | 9 | [regressions-final](runs/regressions-final/summary.json)，含单D01/加入D02、生效前后、混合状态、用户偏好和4K替换 |
| 记忆语义 | 7 | [memory-final](runs/memory-final/summary.json)，跨窗、换题、纠正、1080p旧历史下重载4K |
| 资料变更实验重放 | 2 | [personal-final](runs/personal-final/summary.json)，重放先前独立代理提出的MOV→WEBM预期；AI沿用既有预期重放，不记作新的独立提案或候选人手工操作 |
| 新锚点连续追问 | 2 | [fresh第一轮](runs/anchor-final/fresh-t1.json)、[第二轮](runs/anchor-final/fresh-t2.json) |
| 旧污染锚点连续追问 | 2 | [legacy第一轮](runs/anchor-final/legacy-t1.json)、[第二轮](runs/anchor-final/legacy-t2.json)、[明确标注的历史注入fixture](runs/anchor-final/legacy-fixture.json) |

## 原始证据

- [当前未完成审计](evidence-index-incomplete.json)
- [当前124项测试](offline-tests-release.txt)
- [实际HTTP](http-validated.json)
- [两份原始失败索引](baseline-failures.json)
- [运行前正反例](anchor-cases.json)
- [安装](install.txt)
- [初次测试](offline-tests-initial.txt)
- [定向初次输出](anchor-tests.txt)
- [4项定向测试](anchor-tests-final.txt)
- [runs/memory](runs/memory/summary.json)
- [最终124项测试](offline-tests-repair.txt)
- [失败说明](anchor-reload-preflight-failure.json)
- [预期](runs/anchor-final/pre-run-expectations.json)
- [core-final](runs/core-final/summary.json)
- [regressions-final](runs/regressions-final/summary.json)
- [memory-final](runs/memory-final/summary.json)
- [personal-final](runs/personal-final/summary.json)
- [fresh第一轮](runs/anchor-final/fresh-t1.json)
- [第二轮](runs/anchor-final/fresh-t2.json)
- [legacy第一轮](runs/anchor-final/legacy-t1.json)
- [第二轮](runs/anchor-final/legacy-t2.json)
- [明确标注的历史注入fixture](runs/anchor-final/legacy-fixture.json)
- [79场景矩阵](acceptance-matrix.md)
- [结构化索引](acceptance-matrix.json)
- [审计索引](evidence-index.json)
