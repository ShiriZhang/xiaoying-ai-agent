# 记忆内容边界修复与真实回归

修复有效锚点保存具体企业结论的问题，同时处理新锚点及旧数据库快照再次使用。保持三字段、同次finish、8/6预算及业务/记忆失败隔离，不新增模型请求、工具或用户故障参数。

内容检查曾误拒“报销所需提交材料”，也出现议题前缀拼接旧冲突结论的绕过。补充合法事项、分句和拼接反例后复验；有限检查仍不是通用语义分类器。

最终五组40轮的模块指纹与当前业务源码一致，65处引用匹配各自原文与本轮read-set。两条新增链路先确认30/15冲突，再隔离修改为45天并明确替代、显式重载、同会话追问；均读取新D02回答45天。旧污染锚点fixture明确标注，重开仓储后不再注入系统锚点，原历史保留。

124项测试及实际HTTP通过。真实验证期间曾HTTP402中断，中断索引保留；恢复后在新目录复跑，core-resumed与regressions-resumed为最终核心/规则组，memory-validated、personal-validated及anchor-validated为其余最终组。全部历史138任务/474模型尝试的已知费用估算5.043826元，另2次usage未知；不是实际账单。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 检查 | 结果与证据 |
| --- | --- |
| 离线工程/API测试 | [124项全部通过](offline-tests-release.txt)，0失败/错误/跳过，7.239秒 |
| 实际Mock服务与README请求 | [13次HTTP](http-validated.json)、[PowerShell](powershell-validated.json)，两轮、会话隔离和进程重启通过；外部网络/BGE访问被阻断 |
| 核心六类各两次 | [core-resumed](runs/core-resumed/summary.json)，18轮，含住房补贴、天气、完整两轮及临时/持续read故障 |
| 规则/部分结果 | [regressions-resumed](runs/regressions-resumed/summary.json)，9轮，含单D01/加入D02、已/未生效、混合状态、用户偏好及4K替换 |
| 记忆语义 | [memory-validated](runs/memory-validated/summary.json)，7轮，跨窗、换题/纠正及旧1080p历史下重载4K |
| 资料变更实验重放 | [personal-validated](runs/personal-validated/summary.json)，2轮，MOV→WEBM；AI沿用运行前预期重放，不记作新的独立提案或候选人手工操作 |
| 新旧锚点连续追问 | [anchor-validated](runs/anchor-validated/summary.json)，4轮，两条完整真实链路 |
| 当前版本及全部费用记录 | [恢复后严格审计](evidence-index-resumed.json)，最终40轮模块指纹与安装包/src一致，原失败SHA未变；引用匹配该次read-set及各自快照 |

## 复现命令

先按[README](../../README.md)安装依赖，准备固定revision权重并配置本地.env。以下命令使用真实模型、产生费用，输出目录须尚不存在：

```powershell
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output .cache/core-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group regressions --output .cache/regressions-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group memory --output .cache/memory-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group personal --cases-file examples/batch-8/personal/cases.json --output .cache/personal-new
.venv/Scripts/python.exe -I examples/batch-11/run_anchor_reload.py --live --env-file .env --weights models/bge-small-zh-v1.5 --revision 7999e1d3359715c523056ef9478215996d62a620 --output .cache/anchor-new
```

## 原始证据

- [两份原始失败索引](baseline-failures.json)
- [正反例](anchor-cases.json)
- [首次124测试](offline-tests-initial.txt)
- [定向原输出](anchor-tests.txt)
- [定向复跑](anchor-tests-final.txt)
- [runs/memory](runs/memory/summary.json)
- [预检失败](anchor-reload-preflight-failure.json)
- [未完成审计](evidence-index-incomplete.json)
- [服务中断记录](verification-before-resume.md)
- [124项全部通过](offline-tests-release.txt)
- [13次HTTP](http-validated.json)
- [PowerShell](powershell-validated.json)
- [core-resumed](runs/core-resumed/summary.json)
- [regressions-resumed](runs/regressions-resumed/summary.json)
- [memory-validated](runs/memory-validated/summary.json)
- [personal-validated](runs/personal-validated/summary.json)
- [anchor-validated](runs/anchor-validated/summary.json)
- [运行前预期](runs/anchor-validated/pre-run-expectations.json)
- [历史污染fixture路径](runs/anchor-validated/legacy-fixture.json)
- [fresh第一轮](runs/anchor-validated/fresh-t1.json)
- [fresh第二轮](runs/anchor-validated/fresh-t2.json)
- [legacy第一轮](runs/anchor-validated/legacy-t1.json)
- [legacy第二轮](runs/anchor-validated/legacy-t2.json)
- [79场景矩阵](acceptance-matrix.md)
- [结构化索引](acceptance-matrix.json)
- [该版本最终语义审阅](independent-semantic-review.json)
- [文件、链接与密钥检查](delivery-check-release.json)
