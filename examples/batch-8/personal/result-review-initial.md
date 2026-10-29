# 8.5 独立代理代办：真实变更与引用核查

日期：2026-10-29，America/New_York。执行与核查者为独立代理 `batch8_personal_delegate`，不同于主实现代理。用户已明确授权代理代办，原话见[运行前提案](proposal-before-run.md)；本记录不声称用户亲自提出、修改、运行或核查，也不把代理活动计为个人工时。

## 预期先于运行

提案和用例在文件系统中的首次写入时间为2026-10-29 18:30:59（-04:00）；真实运行metadata.started_at为2026-10-29T18:36:49.599504-04:00。提案先独立选择D09导出格式`MP4、MOV → MP4、WEBM`，并预先规定同会话第二轮必须用新正文、新指纹，不能把旧MOV结论继续当作当前能力。未在看到实际结果后修改预期。

## 实际命令与证据

```powershell
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group personal --cases-file examples/batch-8/personal/cases.json --output examples/batch-8/runs/personal-initial
.venv/Scripts/python.exe -I examples/batch-8/personal/verify_personal.py
```

真实命令使用项目已有官方DeepSeek适配和本地CPU BGE，不替换为脚本模型。受控部分仅为隔离资料副本的指定条文替换、显式RetrievalStore.reload和同会话问题。基础`data/knowledge.json`与修改前完整快照逐字段一致，未改动。

- [运行配置/实际代码指纹](../runs/personal-initial/metadata.json)
- [运行前用例副本](../runs/personal-initial/pre-run-cases.json)
- [第一轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t1-9953d78fdf434eb188e4f34d2a3e0158.json)
- [第二轮完整结果与Trace](../runs/personal-initial/delegate-export-format-change-r1-t2-5c96abee198841f79bd4071c1e164e99.json)
- [用量与执行汇总](../runs/personal-initial/summary.json)

## 独立语义与原文核查

| 项目 | 第一轮实际 | 第二轮实际 | 核查结论 |
| --- | --- | --- | --- |
| 输入 | 星帆剪辑支持哪些视频导出格式？ | 那现在支持哪些导出格式？ | 同会话指代续问 |
| 回答 | 星帆剪辑支持将视频导出为 MP4、MOV 格式。[C1] | 按现行《星帆剪辑导出格式说明》（版本/生效日期 2026-01-01），星帆剪辑支持将视频导出为 MP4、WEBM 格式。[C1] | 与预先规定的旧/新主体分别一致；第二轮当前答案未残留MOV |
| 状态 | answered / finished | answered / finished | 两轮均合法结束 |
| 本轮read-set | D09-P01 | D09-P01 | 重载后新任务重新读取，没有沿用旧read-set |
| 引用 | [C1]，D09-P01，版本/生效日期均2026-01-01 | [C1]，D09-P01，相同日期 | ID/日期保持；原文从各自快照逐字回填 |
| 资料指纹 | sha256:47bf2f316d7b84615a1fe9807faeaace4c84e50395c767af0dfc4d84bd8d2ce1 | sha256:745d8361f96a4b7fa4d230e6c375d2cc88f5a6cb847f6ed2babc6c4325fcd1c9 | 正文变化导致指纹变化 |
| 动作 | search → read → finish | search → read → finish | 模型真实选择；预期未固定完整顺序 |
| 查询规模 | 未传limit，默认6 | 模型选择limit=12 | 第二轮看到历史与候选差异后实际读取；没有程序强行安排变更查询 |
| 计数 | 模型3、工具2、修正0、恢复0 | 模型3、工具2、修正0、恢复0 | 未新增记忆提取请求 |

两轮canonical引文的第一行出处头完全相同；第二行分别为：

```text
星帆剪辑支持将视频导出为 MP4、MOV 格式。
星帆剪辑支持将视频导出为 MP4、WEBM 格式。
```

逐字段对照两个完整语料快照，仅D09这一条文主体有上述替换，其他文档与D09元信息未改变。[C1]紧邻导出格式结论，其正文直接支持该结论。第二轮“现行”在本实验中指本任务使用的新快照，不意味着另造了一个新生效日期或正式新版本。

第二轮history_selection选入第一轮用户和助手消息，input.context中确实保留旧MOV答案与旧引用；memory_update.before也等于首轮合法锚点。尽管旧结论可见，第二轮模型仍用本轮新D09正文回答WEBM，并附新指纹引用。两个实际响应模型标识均为`deepseek-flash`，向量配置均为真实本地`BAAI/bge-small-zh-v1.5`、固定revision、CPU。

## 费用和时间归属

第一轮usage：输入11012、输出473 tokens，保守估算0.025808元；第二轮输入13999、输出551 tokens，保守估算0.032406元。两轮合计输入25011、输出1024 tokens，已知估算0.058214元，未知usage请求0。费率沿用运行记录的2026-10-29未缓存高峰参考，属于估算；invoice_cny仍为null，未核实实际账单或账号余额。

代理阶段观察窗：提案核对始于18:30:12.7179619-04:00，文件完成18:30:59；等待主代理准备通用runner后，执行准备/运行/初读结果的观察窗为18:36:37.2815438至18:37:19.9501007-04:00，含启动和等待，不能称为人类主动工时。runner的elapsed_seconds为12.016秒（不含此前BGE初始化），两轮结果各自elapsed_seconds为4.672秒与5.203秒。后续独立核查和记录另由本代理完成，不倒推个人投入。用户个人主动工时仍未记录；没有本轮亲自操作证据。

## 判定和限制

本用例符合运行前提案预期，独立AI代理对实际答案及逐字引文的核查通过；离线复核脚本也通过。此次没有观察到需要修复或复跑的个人组失败。没有改变预期来适配输出。

这是一组资料差分、两轮真实请求的小样本，不是泛化或统计稳定性证明；也不等同于用户本人审阅。它只覆盖用户本轮明确授权的独立代理代办变更验证，不代替其余六类重复运行、真实记忆场景或冷启动验收。运行源代码版本以metadata中的runtime_source_fingerprints为准；若主实现之后再改变影响本用例的模型指令，应保留本记录并另行复跑，而非覆盖。
