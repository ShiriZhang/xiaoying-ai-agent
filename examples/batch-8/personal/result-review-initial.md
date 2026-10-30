# 资料变更实验：初次运行

独立AI先提出预期，再执行隔离资料修改与实际请求。两轮均search→read→finish，分别回答MP4/MOV和MP4/WEBM；引用逐字对应各自D09，资料指纹改变，历史旧MOV未压过新原文。

这次实验符合原预期，没有观察到该组业务失败。两轮已知费用估算0.058214元，实际账单未知；程序与代理耗时不计为候选人个人工时。后续因共享模型指令变化做新版本回归，保留本次记录。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

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
- [运行配置/实际代码指纹](../runs/personal-initial/metadata.json)
- [运行前用例副本](../runs/personal-initial/pre-run-cases.json)
- [第一轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t1-9953d78fdf434eb188e4f34d2a3e0158.json)
- [第二轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t2-5c96abee198841f79bd4071c1e164e99.json)
- [用量与执行汇总](../runs/personal-initial/summary.json)
