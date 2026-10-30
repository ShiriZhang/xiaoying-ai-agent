# 资料变更实验：结果与版本对照

独立AI代理在运行前提出D09的MOV→WEBM变更、记录预期并执行，后续共享指令变化时重复验证。各版本均保留独立目录、配置及原始输出，未把AI操作记为候选人手工实验。

两轮答案分别由原、新D09正文支持；第二轮实际选入含MOV的历史仍重新读新正文并答WEBM，引用ID/日期保持而指纹改变。该固定资料差分通过，不代表统计泛化。

下表及链接保留各次源码的结果；最新业务源码的实验重放见[完整回归](../../batch-11/verification.md)。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 运行与保留路径 | agent.py实际指纹 | models.py实际指纹 | 已知估算费用 | 未知usage |
| --- | --- | --- | ---: | ---: |
| [personal-initial](../runs/personal-initial/summary.json) | 6eef43319cb1207764c514714bde22b6af1f2629ea45c164a52dc545891dddc5 | 9368097755db61a47fe8da7aff0b04dbab88fe115f5caaf41280d9f7bc4cdca5 | 0.058214元 | 0 |
| [personal-final](../runs/personal-final/summary.json) | 8b78d2a859bedfd842fbfad3812860485f048c11de576b728514d2a92bb7f1e4 | a82b210a1435aeb82d256793812567bb0d034704097be8d32e55dd18b9852ab6 | 0.055856元 | 0 |
| [personal-validated](../runs/personal-validated/summary.json) | 1e4743a44d3bb1046460da233d69ea9323d78253fb1c6f16ff32e986ca30265b | a82b210a1435aeb82d256793812567bb0d034704097be8d32e55dd18b9852ab6 | 0.056706元 | 0 |

| 复核项 | 最终源码实际结果 |
| --- | --- |
| 第一轮答案 | 星帆剪辑支持将视频导出为 MP4、MOV 格式。[C1] |
| 第二轮答案 | 按现行《星帆剪辑导出格式说明》（版本日期、生效日期均为 2026-01-01），星帆剪辑支持将视频导出为 MP4、WEBM 格式。[C1] |
| 状态与动作 | 两轮均answered/finished；各search → read D09-P01 → finish；模型3、工具2、修正0、恢复0 |
| 引用与快照 | 两轮[C1]均逐字等于各自D09-P01；保持日期/ID；指纹仍为47bf…旧快照 → 745d…新快照，与初跑相同 |
| 旧历史污染核查 | 第二轮确实选入包含旧MOV的首轮历史和合法产品锚点，但当前答案不含MOV，重新read新D09并回答WEBM |
| 隔离与持久化 | 仅隔离副本D09主体变更，基础资料仍逐字段等于旧快照；两轮memory_valid、memory_persisted、persistence.saved均true |

| 运行 | agent.py实际指纹 | models.py实际指纹 | 已知估算费用 | 未知usage |
| --- | --- | --- | ---: | ---: |
| personal-initial | 6eef43319cb1207764c514714bde22b6af1f2629ea45c164a52dc545891dddc5 | 9368097755db61a47fe8da7aff0b04dbab88fe115f5caaf41280d9f7bc4cdca5 | 0.058214元 | 0 |
| personal-final | 8b78d2a859bedfd842fbfad3812860485f048c11de576b728514d2a92bb7f1e4 | a82b210a1435aeb82d256793812567bb0d034704097be8d32e55dd18b9852ab6 | 0.055856元 | 0 |

| 项目 | 第一轮实际 | 第二轮实际 | 核查结论 |
| --- | --- | --- | --- |
| 输入 | 星帆剪辑支持哪些视频导出格式？ | 那现在支持哪些导出格式？ | 同会话指代续问 |
| 回答 | 星帆剪辑支持将视频导出为 MP4、MOV 格式。[C1] | 按现行《星帆剪辑导出格式说明》（版本/生效日期 2026-01-01），星帆剪辑支持将视频导出为 MP4、WEBM 格式。[C1] | 与预先规定的旧/新主体分别一致；第二轮当前答案未残留MOV |
| 状态 | answered / finished | answered / finished | 两轮均合法结束 |
| 该次read-set | D09-P01 | D09-P01 | 重载后新任务重新读取，没有沿用旧read-set |
| 引用 | [C1]，D09-P01，版本/生效日期均2026-01-01 | [C1]，D09-P01，相同日期 | ID/日期保持；原文从各自快照逐字回填 |
| 资料指纹 | sha256:47bf2f316d7b84615a1fe9807faeaace4c84e50395c767af0dfc4d84bd8d2ce1 | sha256:745d8361f96a4b7fa4d230e6c375d2cc88f5a6cb847f6ed2babc6c4325fcd1c9 | 正文变化导致指纹变化 |
| 动作 | search → read → finish | search → read → finish | 模型真实选择；预期未固定完整顺序 |
| 查询规模 | 未传limit，默认6 | 模型选择limit=12 | 第二轮看到历史与候选差异后实际读取；没有程序强行安排变更查询 |
| 计数 | 模型3、工具2、修正0、恢复0 | 模型3、工具2、修正0、恢复0 | 未新增记忆提取请求 |

## 原始证据

- [运行前提案](proposal-before-run.md)
- [result-review-final.md](result-review-final.md)
- [review-final.json](review-final.json)
- [最新配置/源码指纹](../runs/personal-validated/metadata.json)
- [第一轮完整结果](../runs/personal-validated/delegate-export-format-change-r1-t1-19521e7dfaac44f48098446571804c83.json)
- [第二轮完整结果](../runs/personal-validated/delegate-export-format-change-r1-t2-c438d247309a42f4851118c5902ac4a8.json)
- [汇总](../runs/personal-validated/summary.json)
- [personal-initial](../runs/personal-initial/summary.json)
- [personal-final](../runs/personal-final/summary.json)
- [personal-validated](../runs/personal-validated/summary.json)
- [result-review-initial.md](result-review-initial.md)
- [review-initial.json](review-initial.json)
- [配置/源码指纹](../runs/personal-final/metadata.json)
- [第一轮](../runs/personal-final/delegate-export-format-change-r1-t1-2d9702a9a37840f59972740c6f206f6e.json)
- [第二轮](../runs/personal-final/delegate-export-format-change-r1-t2-9687fd88ff87426f9ce3b50578d77f88.json)
- [汇总](../runs/personal-final/summary.json)
- [运行配置/实际代码指纹](../runs/personal-initial/metadata.json)
- [运行前用例副本](../runs/personal-initial/pre-run-cases.json)
- [第一轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t1-9953d78fdf434eb188e4f34d2a3e0158.json)
- [第二轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t2-5c96abee198841f79bd4071c1e164e99.json)
- [用量与执行汇总](../runs/personal-initial/summary.json)
