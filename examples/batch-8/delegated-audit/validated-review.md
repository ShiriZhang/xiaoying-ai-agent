# 第八批最终真实记录：独立代理语义核查

审查者为用户本轮明确授权的独立AI证据核查代理，不是主实现代理，也不记作用户本人亲自修改、运行或审阅。资料修改代理的运行前预期与用户授权原话见[个人组提案](../personal/proposal-before-run.md)。本报告不改写预期，不删除失败，不从代理活动推算个人工时。

## 范围与结论

已逐个读取最终四组36个真实任务轮次的实际答案、引用原文、工具动作/观察、缺口、关键追问及锚点/历史前后。最终四组为`core-validated`（18轮）、`regressions-validated`（9轮）、`memory-validated`（7轮）、`personal-validated`（2轮）。四组metadata的全部runtime_source_fingerprints一致，temperature均为0；使用真实DeepSeek与真实CPU BGE，未以Mock替换模型。

在这些固定输入与实际运行上，最终36轮符合各自预先记录的业务/故障/变体/记忆预期。所有已发布引用都已逐条对照实际语料快照：连续text逐字一致，doc_id、version_date、passage_id、内容指纹、本轮read-set相符；引用所关联的材料、产品能力、期限双方或生效替代判断获得原文支持。持续故障预期就是incomplete，不能把它记成“已回答成功”。

这不是自动机械判定：曾有机械状态/引用检查满足、但额外片面期限错误或未读补查候选的中间轮次，被本代理判为未通过并保留。出处存在不能证明语义；本报告是在阅读实际结论与原文后作出的独立AI核查，不冒充人类审阅，也不证明泛化或统计稳定性。

## 最终逐用例矩阵

下表每行均有实际文件链接。`M/T`为模型尝试/业务工具次数；“通过”仅指该轮满足该用例预期。

<!-- The linked matrix below is generated only to format already inspected results. -->

| 用例/独立次数/轮次 | 实际状态 | M/T | 引用片段 | 独立核查 |
| --- | --- | --- | --- | --- |
| [A01 / r1 / t1](../runs/core-validated/A01-r1-t1-a063cfa12d424a02bbcb9936c3cfc991.json) | answered | 3/2 | D03-P01, D04-P01 | 通过本用例预期：材料仅发票/出差审批单；如附审批流则另由D04支持，无片面期限。 |
| [A01 / r2 / t1](../runs/core-validated/A01-r2-t1-b7f09179d0bc464a8d07838751190cca.json) | answered | 3/2 | D03-P01 | 通过本用例预期：材料仅发票/出差审批单；如附审批流则另由D04支持，无片面期限。 |
| [A02 / r1 / t1](../runs/core-validated/A02-r1-t1-97edf89e80624707aca3cc60ae44fcf3.json) | needs_clarification | 5/4 | D01-P01, D02-P01, D03-P01, D04-P01 | 通过本用例预期：双侧30/15均保留；补查后实际read D03/D04；不选边，单个依据请求。 |
| [A02 / r2 / t1](../runs/core-validated/A02-r2-t1-0bfcf9c0baf741b7aff0eec4734f39e3.json) | needs_clarification | 5/4 | D01-P01, D02-P01, D03-P01, D04-P01 | 通过本用例预期：双侧30/15均保留；补查后实际read D03/D04；不选边，单个依据请求。 |
| [A03-missing / r1 / t1](../runs/core-validated/A03-missing-r1-t1-c3851f68786f4bf09fde74116d4f8fa1.json) | insufficient_evidence | 4/3 | D08-P01 | 通过本用例预期：补查后只说明未覆盖、不确认有无；D08支持人事服务台指引。 |
| [A03-missing / r2 / t1](../runs/core-validated/A03-missing-r2-t1-9c958e218e764bc58b006479378c57a9.json) | insufficient_evidence | 4/3 | D08-P01 | 通过本用例预期：补查后只说明未覆盖、不确认有无；D08支持人事服务台指引。 |
| [A03-weather / r1 / t1](../runs/core-validated/A03-weather-r1-t1-4fdd0a1bf7a9427793785953a00cd5ef.json) | out_of_scope | 1/0 | 无企业事实引用 | 通过本用例预期：说明公司资料服务边界，不提供天气，无追问。 |
| [A03-weather / r2 / t1](../runs/core-validated/A03-weather-r2-t1-f54ca2097aca4740b958e300f3aaa216.json) | out_of_scope | 1/0 | 无企业事实引用 | 通过本用例预期：说明公司资料服务边界，不提供天气，无追问。 |
| [A04 / r1 / t1](../runs/core-validated/A04-r1-t1-49a375a616724e6f8f5660b0c7b8c376.json) | answered | 3/2 | D03-P01 | 通过本用例预期：口语材料含义保持，仅两项必交材料，由D03支持。 |
| [A04 / r2 / t1](../runs/core-validated/A04-r2-t1-f8a93eb0cf234947ab540ce4720a1288.json) | answered | 3/2 | D03-P01 | 通过本用例预期：口语材料含义保持，仅两项必交材料，由D03支持。 |
| [A05 / r1 / t1](../runs/core-validated/A05-r1-t1-e04ede69845e40cfa5c2b35b3a4fde12.json) | answered | 3/2 | D09-P01 | 通过本用例预期：首轮MP4/MOV由D09支持，合法产品锚点。 |
| [A05 / r1 / t2](../runs/core-validated/A05-r1-t2-b962bd94a2b941cf9800228dbca435ab.json) | answered | 3/2 | D10-P01 | 通过本用例预期：第二轮新检索/read D10支持1080p，focus更新，无旧摘要替代。 |
| [A05 / r2 / t1](../runs/core-validated/A05-r2-t1-1d4cc426a118432ca978a954c33d3b4e.json) | answered | 3/2 | D09-P01 | 通过本用例预期：首轮MP4/MOV由D09支持，合法产品锚点。 |
| [A05 / r2 / t2](../runs/core-validated/A05-r2-t2-77d36f6285a5407c93c5c198bc82e5d0.json) | answered | 3/2 | D10-P01 | 通过本用例预期：第二轮新检索/read D10支持1080p，focus更新，无旧摘要替代。 |
| [A06-persistent / r1 / t1](../runs/core-validated/A06-persistent-r1-t1-b500addf1b1f4c8586b68a502a47e6ff.json) | incomplete | 3/3 | 无企业事实引用 | 通过本用例预期：唯一恢复仍失败即停止，无额外收尾、伪引文或资料缺失说法。 |
| [A06-persistent / r2 / t1](../runs/core-validated/A06-persistent-r2-t1-746062a4c9ab45198da7831486b466b7.json) | incomplete | 3/3 | 无企业事实引用 | 通过本用例预期：唯一恢复仍失败即停止，无额外收尾、伪引文或资料缺失说法。 |
| [A06-temporary / r1 / t1](../runs/core-validated/A06-temporary-r1-t1-aceefa4962154ae79819b6ab3462dfe0.json) | answered | 4/3 | D03-P01 | 通过本用例预期：真实read首错后模型选唯一恢复，D03成功；无伪造材料或执行错误混入缺口。 |
| [A06-temporary / r2 / t1](../runs/core-validated/A06-temporary-r2-t1-a9dd6c5e31824f7294554e1449863de4.json) | answered | 4/3 | D03-P01 | 通过本用例预期：真实read首错后模型选唯一恢复，D03成功；无伪造材料或执行错误混入缺口。 |
| [added-D02 / r1 / t1](../runs/regressions-validated/added-D02-r1-t1-32e8f710050e4d1d99241ff6e02b65fd.json) | needs_clarification | 4/3 | D01-P01, D02-P01 | 通过本用例预期：两文档均读并补查；无新候选不虚构第三份资料，保留冲突。 |
| [effective / r1 / t1](../runs/regressions-validated/effective-r1-t1-e70f83d6b44549cabf45e4946d222f6b.json) | answered | 3/2 | D06-P01, D05-P01 | 通过本用例预期：2026-10-29按1工作日；D06明确已生效并替代D05。 |
| [future / r1 / t1](../runs/regressions-validated/future-r1-t1-1c13361b762347edad91984cc08aecfa.json) | answered | 3/2 | D05-P01, D06-P01 | 通过本用例预期：2026-09-30仍2工作日；D06尚未生效，保留日期依据。 |
| [partial-conflict / r1 / t1](../runs/regressions-validated/partial-conflict-r1-t1-3d24c575e3b14b5a9de3f7137b8172e5.json) | needs_clarification | 5/4 | D03-P01, D01-P01, D02-P01, D04-P01 | 通过本用例预期：材料保留；期限双侧与补查D04均有引用；待澄清和单关键追问。 |
| [partial-missing / r1 / t1](../runs/regressions-validated/partial-missing-r1-t1-85b7f54177ce4748b50e08c3c516b521.json) | insufficient_evidence | 6/4 | D03-P01, D04-P01, D08-P01 | 通过本用例预期：保留材料，补贴缺口单列；人事咨询指引有D08支持。 |
| [partial-weather / r1 / t1](../runs/regressions-validated/partial-weather-r1-t1-a9114ba4aaee49ab891837c4675e75c0.json) | out_of_scope | 4/2 | D03-P01 | 通过本用例预期：保留材料，天气边界单列；整体out_of_scope。 |
| [replacement / r1 / t1](../runs/regressions-validated/replacement-r1-t1-c69ef5e15fe2406e9142f665cc122c6f.json) | answered | 3/2 | D10-P01 | 通过本用例预期：隔离D10重载后用新4K正文/指纹，不复用1080p。 |
| [single-D01 / r1 / t1](../runs/regressions-validated/single-D01-r1-t1-f11b2881318745ef8f21674db2703f2d.json) | answered | 3/2 | D01-P01 | 通过本用例预期：仅D01时按30天，不强行制造冲突。 |
| [user-preference / r1 / t1](../runs/regressions-validated/user-preference-r1-t1-1c625742953c42fab1c63538bdaa02fd.json) | needs_clarification | 5/4 | D01-P01, D02-P01, D03-P01, D04-P01 | 通过本用例预期：偏好不裁决；双侧+补查D03/D04，单个现行依据请求。 |
| [cross-window / r1 / t1](../runs/memory-validated/cross-window-r1-t1-19afdef85aaa4df6bc1aced83491ee51.json) | answered | 3/2 | D09-P01 | 通过本用例预期：首轮D09支持MP4/MOV，只存对象/事项。 |
| [cross-window / r1 / t2](../runs/memory-validated/cross-window-r1-t2-b041bb171c3944b49ba1158b3f4a6594.json) | answered | 3/2 | D10-P01 | 通过本用例预期：原始历史选入为空，仍由产品锚点理解对象，再读D10回答1080p。 |
| [old-conclusion / r1 / t1](../runs/memory-validated/old-conclusion-r1-t1-223d104fa2f748b59f25892b9a2a7a76.json) | answered | 3/2 | D10-P01 | 通过本用例预期：首轮D10支持1080p，只存对象/事项。 |
| [old-conclusion / r1 / t2](../runs/memory-validated/old-conclusion-r1-t2-0482cf3cf45f4665956b5f9372c976ae.json) | answered | 3/2 | D10-P01 | 通过本用例预期：旧1080p历史可见仍重新读新D10回答4K，引用新指纹。 |
| [switch-correct / r1 / t1](../runs/memory-validated/switch-correct-r1-t1-305e1997c31f4216aa31aa5c9e44a28f.json) | answered | 3/2 | D09-P01 | 通过本用例预期：产品导出格式，D09支持；不存格式答案。 |
| [switch-correct / r1 / t2](../runs/memory-validated/switch-correct-r1-t2-ee757ad2cdc340168dbd4ced8a6f68b6.json) | answered | 3/2 | D03-P01 | 通过本用例预期：明确换题为报销，读D03、subject/focus更新。 |
| [switch-correct / r1 / t3](../runs/memory-validated/switch-correct-r1-t3-aea047b14dcb4657a458fb32e87680f3.json) | answered | 3/2 | D11-P01 | 通过本用例预期：纠正为产品字幕，读D11、清除过时报销事项。 |
| [delegate-export-format-change / r1 / t1](../runs/personal-validated/delegate-export-format-change-r1-t1-19521e7dfaac44f48098446571804c83.json) | answered | 3/2 | D09-P01 | 通过本用例预期：修改前D09支持MP4/MOV，符合独立预期。 |
| [delegate-export-format-change / r1 / t2](../runs/personal-validated/delegate-export-format-change-r1-t2-c438d247309a42f4851118c5902ac4a8.json) | answered | 3/2 | D09-P01 | 通过本用例预期：旧MOV历史可见，重载后D09支持MP4/WEBM，新指纹、基础语料不变。 |

## 关键语义与动态路径

- 材料与口语改写：均以D03支持发票和出差审批单，不补造其他必需材料。个别轮次附带审批流程，D04也逐字支持；这是有依据的额外说明，没有再发布未消解期限。边界说明只说其他类型材料未被现有资料覆盖，不断言公司不存在其他制度。
- 冲突：最终A02两次均实际执行search→read D01/D02→修改查询补查search→read D03/D04→finish，5模型/4工具。仍无法消解时分别保留30/15天及出处，只请求一份能确认现行规则的资料；不按日期、偏好或“临时从严建议”选边。材料+期限、用户偏好也实际读取补查新同主题候选。
- 隔离加入D02仅有两份文档，补查后没有任何新未读候选，故直接保留冲突结束合理；没有虚构第三份资料。这与完整语料下补查后再读取其他同主题候选的路径不同，不要求所有场景同一工具序列。
- 住房补贴：核心两次有真实补充检索，说明不能确认有无，D08只支持人事服务台指引；未将未查到说成公司没有补贴。天气两次不提供天气答案，也无无意义追问。
- 真实工具故障：临时read错误后由真实模型选择一次恢复、读取D03成功；错误仍在execution_issues，gaps不混入执行故障。持续read错误两次均唯一恢复再失败后立即recovery_exhausted停止，没有额外模型收尾、伪造引文或伪装资料不足。
- 混合状态：材料+冲突为needs_clarification，材料+缺失为insufficient_evidence，材料+天气为out_of_scope，均保留已支持材料；执行中断则incomplete。关键追问最多一个，没有以多个问号打包问题。
- 生效/替代：2026-10-29按新版提前1工作日，2026-09-30按旧版提前2工作日，引用D05/D06正文支持日期与明确替代；测试冻结日期未变成公开历史时点功能。
- 至少两种实际决策路径明确存在：正常材料3模型/2工具、冲突5模型/4工具、天气1模型/0工具、临时故障4模型/3工具、持续故障3模型/3工具。冲突和住房补贴的query确实根据观察改变，并实际再次执行检索，不是预设假Trace。

## 记忆与资料差分

跨窗口第二轮预算为1，选入历史为空、原两条消息列入omitted；产品对象来自合法subject锚点，仍重新search/read D10回答1080p。focus由导出格式更新为分辨率，没有保存MP4/MOV或1080p答案。

换题/纠正三轮从星帆剪辑导出格式→星帆科技报销材料→星帆剪辑自动字幕；每轮重新读取对应D09/D03/D11，subject/focus随用户新表述更新，第三轮不残留报销对象或关注事项。锚点来源为对应会话消息，pending_clarification无未解决事项时为空。

旧结论污染用例第一轮1080p；第二轮原始历史确有1080p及旧引用，但隔离正文替换/重载后实际引用新D10与新指纹，回答4K。个人组同理从MP4/MOV→MP4/WEBM，旧MOV可见却未压过本轮新D09；只改预定条文主体，基础语料不变。这里的“现行”指本任务使用的测试快照，不宣称另造正式新生效公司文件。

已读锚点中未发现可直接复用的企业答案、逐字引文或员工画像。冲突focus/pending里的“15天还是30天”是待澄清问题，不是已定制度；不能把它作为下一轮证据。结构来源合法本身不构成此语义结论，本代理已读各字段实际值。

## 去重费用与工时归属

独立提取器见[extract_evidence.py](extract_evidence.py)，只按顶层`result.request_id`去重、只计顶层`model_response/model_error`的usage；滚动progress、summary和内嵌历史不再累加。实际语料文件还通过加载器重新计算指纹核对。派生的[最终36轮明细](validated-extracted.json)与[所有历史尝试明细](all-attempts-extracted.json)均保留真实文件路径。

| 运行目录 | 任务轮次 | 模型尝试 | 已知估算人民币 |
| --- | ---: | ---: | ---: |
| core-initial | 18 | 61 | 0.561782 |
| core-repair-1 | 18 | 56 | 0.530964 |
| core-final（中间版本） | 18 | 56 | 0.531408 |
| regressions-final（中间版本） | 9 | 32 | 0.324846 |
| personal-initial | 2 | 6 | 0.058214 |
| personal-final（中间版本） | 2 | 6 | 0.055856 |
| conflict-guidance-check | 1 | 5 | 0.061698 |
| core-validated | 18 | 58 | 0.574484 |
| regressions-validated | 9 | 36 | 0.380280 |
| memory-validated | 7 | 21 | 0.197146 |
| personal-validated | 2 | 6 | 0.056706 |
| **本批所有历史尝试合计** | **104** | **343** | **3.333384** |
| **其中最终四组** | **36** | **121** | **1.208616** |

本批所有104轮的已知prompt为1413580 tokens、completion为63278 tokens，usage未知0；最终四组分别为517968/21585 tokens。费用沿用记录中2026-10-29官方Flash高峰未缓存参考输入2/输出8元每百万token的保守估算，不是服务商账单。账单和余额未核实，不据此声称还剩多少30元预算；更早批次的未知计费也不因本批未知0而消失。

本证据代理已记录的观察窗为2026-10-29 18:30:48至18:54:06（America/New_York，后者为撰写前最后一次时钟读数），包含阅读、派生文件整理与等待，不是精确主动工作时间；后续撰写未倒推计入。真实模型运行/等待的耗时由各summary和结果保存。用户个人工时未提供、无亲自操作记录，不把代理或模型运行时间记为用户个人投入。

## 历史失败与限制

初次4个格式/交付失败及无依据临时15天建议见[初次审查](core-initial-review.md)；第一次修复后A01两次额外发布片面期限见[第一次修复审查](core-repair-1-review.md)；temperature=0后仍未读取补查新候选见[补查阅读修复前审查](pre-guidance-review.md)。原记录保留，不将后来通过改写为从未失败。

最终固定用例核查通过只覆盖本批预定场景与用户授权的独立代理代办方式。少量独立重复不是统计稳定性或通用正确性证明；第9批冷启动、最终综合交付，以及真实账单核对不由本报告代做。
