# 真实36轮的独立语义审阅

独立AI逐轮检查该历史源码的core-validated18轮、regressions-validated9轮、memory-validated7轮和personal-validated2轮。该版本固定业务预期满足；不能据此保证后来才发现的记忆内容边界。

答案、引用原文、动作、缺口和锚点均有明细。此为AI语义复核，不冒充候选人人工逐条审阅，也不证明泛化稳定性。后续记忆修复后的40轮以[当前评估](../../../docs/03-evaluation.md)为准。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

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
| **该版本所有历史尝试合计** | **104** | **343** | **3.333384** |
| **其中最终四组** | **36** | **121** | **1.208616** |

## 原始证据

- [个人组提案](../personal/proposal-before-run.md)
- [A01 / r1 / t1](../runs/core-validated/A01-r1-t1-a063cfa12d424a02bbcb9936c3cfc991.json)
- [A01 / r2 / t1](../runs/core-validated/A01-r2-t1-b7f09179d0bc464a8d07838751190cca.json)
- [A02 / r1 / t1](../runs/core-validated/A02-r1-t1-97edf89e80624707aca3cc60ae44fcf3.json)
- [A02 / r2 / t1](../runs/core-validated/A02-r2-t1-0bfcf9c0baf741b7aff0eec4734f39e3.json)
- [A03-missing / r1 / t1](../runs/core-validated/A03-missing-r1-t1-c3851f68786f4bf09fde74116d4f8fa1.json)
- [A03-missing / r2 / t1](../runs/core-validated/A03-missing-r2-t1-9c958e218e764bc58b006479378c57a9.json)
- [A03-weather / r1 / t1](../runs/core-validated/A03-weather-r1-t1-4fdd0a1bf7a9427793785953a00cd5ef.json)
- [A03-weather / r2 / t1](../runs/core-validated/A03-weather-r2-t1-f54ca2097aca4740b958e300f3aaa216.json)
- [A04 / r1 / t1](../runs/core-validated/A04-r1-t1-49a375a616724e6f8f5660b0c7b8c376.json)
- [A04 / r2 / t1](../runs/core-validated/A04-r2-t1-f8a93eb0cf234947ab540ce4720a1288.json)
- [A05 / r1 / t1](../runs/core-validated/A05-r1-t1-e04ede69845e40cfa5c2b35b3a4fde12.json)
- [A05 / r1 / t2](../runs/core-validated/A05-r1-t2-b962bd94a2b941cf9800228dbca435ab.json)
- [A05 / r2 / t1](../runs/core-validated/A05-r2-t1-1d4cc426a118432ca978a954c33d3b4e.json)
- [A05 / r2 / t2](../runs/core-validated/A05-r2-t2-77d36f6285a5407c93c5c198bc82e5d0.json)
- [A06-persistent / r1 / t1](../runs/core-validated/A06-persistent-r1-t1-b500addf1b1f4c8586b68a502a47e6ff.json)
- [A06-persistent / r2 / t1](../runs/core-validated/A06-persistent-r2-t1-746062a4c9ab45198da7831486b466b7.json)
- [A06-temporary / r1 / t1](../runs/core-validated/A06-temporary-r1-t1-aceefa4962154ae79819b6ab3462dfe0.json)
- [A06-temporary / r2 / t1](../runs/core-validated/A06-temporary-r2-t1-a9dd6c5e31824f7294554e1449863de4.json)
- [added-D02 / r1 / t1](../runs/regressions-validated/added-D02-r1-t1-32e8f710050e4d1d99241ff6e02b65fd.json)
- [effective / r1 / t1](../runs/regressions-validated/effective-r1-t1-e70f83d6b44549cabf45e4946d222f6b.json)
- [future / r1 / t1](../runs/regressions-validated/future-r1-t1-1c13361b762347edad91984cc08aecfa.json)
- [partial-conflict / r1 / t1](../runs/regressions-validated/partial-conflict-r1-t1-3d24c575e3b14b5a9de3f7137b8172e5.json)
- [partial-missing / r1 / t1](../runs/regressions-validated/partial-missing-r1-t1-85b7f54177ce4748b50e08c3c516b521.json)
- [partial-weather / r1 / t1](../runs/regressions-validated/partial-weather-r1-t1-a9114ba4aaee49ab891837c4675e75c0.json)
- [replacement / r1 / t1](../runs/regressions-validated/replacement-r1-t1-c69ef5e15fe2406e9142f665cc122c6f.json)
- [single-D01 / r1 / t1](../runs/regressions-validated/single-D01-r1-t1-f11b2881318745ef8f21674db2703f2d.json)
- [user-preference / r1 / t1](../runs/regressions-validated/user-preference-r1-t1-1c625742953c42fab1c63538bdaa02fd.json)
- [cross-window / r1 / t1](../runs/memory-validated/cross-window-r1-t1-19afdef85aaa4df6bc1aced83491ee51.json)
- [cross-window / r1 / t2](../runs/memory-validated/cross-window-r1-t2-b041bb171c3944b49ba1158b3f4a6594.json)
- [old-conclusion / r1 / t1](../runs/memory-validated/old-conclusion-r1-t1-223d104fa2f748b59f25892b9a2a7a76.json)
- [old-conclusion / r1 / t2](../runs/memory-validated/old-conclusion-r1-t2-0482cf3cf45f4665956b5f9372c976ae.json)
- [switch-correct / r1 / t1](../runs/memory-validated/switch-correct-r1-t1-305e1997c31f4216aa31aa5c9e44a28f.json)
- [switch-correct / r1 / t2](../runs/memory-validated/switch-correct-r1-t2-ee757ad2cdc340168dbd4ced8a6f68b6.json)
- [switch-correct / r1 / t3](../runs/memory-validated/switch-correct-r1-t3-aea047b14dcb4657a458fb32e87680f3.json)
- [delegate-export-format-change / r1 / t1](../runs/personal-validated/delegate-export-format-change-r1-t1-19521e7dfaac44f48098446571804c83.json)
- [delegate-export-format-change / r1 / t2](../runs/personal-validated/delegate-export-format-change-r1-t2-c438d247309a42f4851118c5902ac4a8.json)
- [extract_evidence.py](extract_evidence.py)
- [最终36轮明细](validated-extracted.json)
- [所有历史尝试明细](all-attempts-extracted.json)
- [初次审查](core-initial-review.md)
- [第一次修复审查](core-repair-1-review.md)
- [补查阅读修复前审查](pre-guidance-review.md)
