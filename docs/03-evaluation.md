# 效果验证

验证分为离线工程测试、真实本地检索和真实模型端到端三个层次。通过标准来自[需求](01-requirements.md)及[能力规格](specs/grounded-qa.md)，以事实、引用和动作行为判定，不固定自然语言措辞。

## 验证结果

| 层次 | 实际结果 | 证据与边界 |
| --- | --- | --- |
| 离线工程/API | 124项全部通过 | [测试输出](../examples/publication-review-2026-10-30/tests.txt)；验证工程契约，不证明真实语义 |
| 实际Mock HTTP | 13次请求，两轮、隔离及重启通过 | [HTTP](../examples/acceptance-final-2026-10-29/http.json)、[PowerShell](../examples/acceptance-final-2026-10-29/powershell.json)；实际服务，受控模拟模型 |
| 真实CPU检索 | 7个输入分别返回6/12候选，共14项召回及重载边界通过 | [真实检索](../examples/acceptance-final-2026-10-29/retrieval/f619369b806944b4b1a8643afdd1d910.json)；无生成模型调用 |
| 真实模型端到端 | 当前业务源码对应40轮，65处引用核对一致 | [证据审计](../examples/publication-review-2026-10-30/business-evidence.json)、[语义审阅](../examples/batch-11/independent-semantic-review.json)；固定样本，不证明泛化 |
| 全规格覆盖 | 79个场景有测试或实际证据映射 | [逐场景矩阵](../examples/batch-11/acceptance-matrix.md)；映射不等于自动语义证明 |
| 独立环境 | 干净副本完成空缓存Mock、独立权重准备及真实HTTP问答 | [环境复现记录](../examples/batch-9/verification.md)；为当时版本，不冒充记忆修复后重新冷安装 |

真实模型为DeepSeek官方deepseek-flash，显式非思考、temperature=0；检索使用真实CPU BGE固定revision与BM25/RRF。日期、配置、源码与资料指纹保存在每组metadata和逐轮Trace中。离线、真实检索和真实生成结果分别解释。

## 六类必验场景

核心组18轮，包含六类各两次、资料缺失/天气及完整上下文两轮；精确文件入口见[矩阵](../examples/batch-11/acceptance-matrix.md)。

| 场景 | 预期 | 实际结果 |
| --- | --- | --- |
| A01 明确答案 | 发票与出差审批单，附支持原文 | 两次均符合，D03支持材料；个别回答附带有D04依据的审批流程 |
| A02 文档冲突 | 读取30/15天双方，补查无裁定依据则待澄清 | 两次均保留双侧冲突及引用，未擅选15天 |
| A03 资料外问题 | 补贴说明未覆盖，天气说明范围 | 均符合，未把未查到解释为公司没有 |
| A04 改写问题 | 口语表达仍识别报销材料 | 两次材料事实与A01一致，引用有效 |
| A05 上下文追问 | 格式→分辨率，理解指代并重新读原文 | 两个独立会话均重新读取D10、回答1080p |
| A06 工具失败 | 真实错误影响下一步，恢复至多一次 | 临时read错误后模型选择恢复；持续失败明确incomplete |

正常路径通常search → read → finish；冲突路径读取双方后改写查询补查、读取新候选再结束。故障路径保留实际错误与模型恢复选择。这些是模型观察工具结果后的动作差异，非固定脚本日志。

## 资料差分与记忆回归

最终40轮包括核心18轮、规则9轮、记忆7轮、独立资料实验重放2轮、新旧锚点连续追问4轮，见[运行分组](../examples/batch-11/verification.md)。

- 仅D01时回答30天；加入D02后转为30/15冲突，不能按用户偏好裁决。
- 人事新规则生效前按旧规定，生效后依据明确替代正文回答；混合问题保留已答部分与未解决事项。
- 1080p→4K、MOV→WEBM后答案及引用随新正文变化，即使历史仍包含旧能力。
- 产品对象移出近期窗口后仍能用合法话题锚点理解指代；换题与纠正更新对象。
- 先形成期限冲突，再把隔离资料改为45天并明确替代、显式重载、同会话追问，两条路径均重新读新D02并回答45天。
- 历史污染锚点作为测试fixture明确标注；重开仓储后不再注入系统锚点，原业务历史保留。

## 引用与语义核查

逐条拆解答案中的企业结论，核对紧邻引用、原文限定条件、冲突双方和适用日期。65处引用均匹配各轮快照的原文、文档ID、版本、指纹和read-set。此项核查由AI审查代理执行，不记作候选人逐条人工审阅。

## 失败与改进

| 已观察失败 | 修改与复验 | 原始记录 |
| --- | --- | --- |
| 裸引用标记、多追问导致格式修正失败 | 明确schema示例和具体反馈后复跑 | [初次真实审阅](../examples/batch-8/delegated-audit/core-initial-review.md) |
| 提出临时从严15天、补查后未读新候选 | 收紧冲突边界，提示已读/未读证据，再做真实回归 | [语义问题](../examples/batch-8/delegated-audit/pre-guidance-review.md) |
| 合法锚点带入旧制度冲突结论 | 新旧快照均检查，正反例及重载连续追问验证 | [原失败](../examples/batch-11/baseline-failures.json)、[修复验证](../examples/batch-11/verification.md) |
| 内容检查误伤合法事项、议题前缀可绕过 | 增加正例、分句和拼接反例，再复跑40轮 | [修复记录](../examples/batch-11/verification.md) |
| HTTP402中断真实验证 | 保留中断记录，在服务恢复后新目录完整复跑 | [中断证据](../examples/batch-11/evidence-index-incomplete.json)、[复跑证据](../examples/batch-11/evidence-index-resumed.json) |
| 本地临时目录权限、SQLite测试连接未关 | 区分环境限制与代码问题，修正连接清理后复跑 | [测试初次输出](../examples/batch-11/offline-tests-initial.txt)、[通过输出](../examples/publication-review-2026-10-30/tests.txt) |

## 限制与改进方向

没有发现固定最终样本中的无依据制度答案或错误引用。仍有低优先输出聚焦问题：材料问答偶尔附带有依据的审批流程。锚点形态检查不是通用语义分类器，可能漏判或误判。

每类重复两次不能证明统计稳定性。只实测Windows/CPython3.12、本机单进程；Reranker、检索消融和更大规模统计评估未做。用量估算与账单分开，未知usage不计为免费。后续优先扩展失败样本、输出聚焦和语义支持性评估。

## 复现

安装与模式配置见[README](../README.md)。离线执行：

```powershell
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-11/audit_evidence.py --output .cache/evidence-new.json
```

真实场景入口为`examples/batch-8/run_live.py`，须显式`--live`，会产生模型费用；命令与独立权重准备见[运行说明](../README.md)。输出采用新路径，保留失败及其对应版本。
