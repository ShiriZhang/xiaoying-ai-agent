# 第十一批：验收后锚点内容边界修复

当前状态：第11批11.1–11.4完成，11.5–11.6未完成，50/52。最终源码124项测试和实际Mock HTTP通过；最终真实回归因DeepSeek HTTP402停止，核心10/18轮、规则8/9轮（各含一轮服务失败），记忆7/7、资料重放2/2、新链路4/4。当前共31/40轮有实际记录，不能把前一版完整40轮当作最终源码通过证据。等待用户处理API余额后再补齐，不提交或推送。

[当前未完成审计](evidence-index-incomplete.json)、[暂停状态](pause-status.json)记录passed=false；不得以旧报告替代。当前累计111任务，已知usage保守估算4.066138元，新增2次usage未知；全项目已知估算子集7.442996元，实际总额和账单仍未知。HTTP402按[官方错误说明](https://api-docs.deepseek.com/quick_start/error_codes/)表示余额不足；没有检查私人账户余额或代充值。

审查发现的“议题前缀＋冒号＋旧冲突结论”绕过已修正，同时覆盖连接词及无分隔符拼接；三个字段36允许项、42拒绝项由独立代理复核通过。[当前124项测试](offline-tests-release.txt)通过，[实际HTTP](http-validated.json)及PowerShell重启演示通过。原80任务报告属于审查修复前版本；随后重跑的*-validated目录才对应当前源码。

以下为余额阻塞前已完成的阶段记录，其中40轮、2.961010元和*-final目录均对应当时版本；它们保留作失败/修复历史，不表示本次最终验收完成。

本批对应11.1–11.6，基线`e1e9ef2cd5376afd68aea7b38c36c755d2dbbfcc`。保持subject/focus/pending_clarification三个字段、同次finish、8/6预算和业务/记忆失败隔离；没有增加记忆模型调用、工具或普通用户故障参数。原始失败与旧源码报告保留，修复后实际结果另存，不修改旧指纹。

## 原失败、修复及局限

[两份原始失败索引](baseline-failures.json)保存A02-r1和added-D02文件的原始SHA-256、原memory_valid/persisted=true及旧校验器实际接受结果；[运行前正反例](anchor-cases.json)区分讨论事项、用户数字问题和企业结论。原文件保持不变，离线测试直接读取原样本验证新校验拒绝。

实现由三部分组成：agent系统指令加入全部字段的正反例；memory.validate_anchor在结构/来源校验之外，对可识别的陈述形态做有限检查；SessionStore.get_session在旧数据库快照再次使用前重检，标为无效并给出安全原因。新锚点非法沿用现有降级，保留合法业务答案、不增加模型/格式修正。旧污染快照不注入下一轮系统锚点，原始历史仍保留；begin_run按原机制先持久失效旧锚点。

检查针对期限/能力陈述和已确认冲突等形态，允许“1080p导出支持情况”等问题；它**不是通用自然语言语义判定器**。任意新措辞仍可能漏判或误判，实际模型生成与语义支持必须另外审阅。不能仅因字段、来源或正则检查通过，就宣称所有自然语言都满足记忆边界。

## 失败、修正与离线结果

- 首次重装受网络/Windows临时目录权限影响；使用已声明依赖的本地缓存与允许临时目录操作后重装成功，见[安装](install.txt)。依赖声明未变。
- 首次124测试中123通过，新增测试未关闭SQLite连接导致Windows清理失败，原输出见[初次测试](offline-tests-initial.txt)；修正为显式关闭并提交。另一次受限临时目录运行失败保存在[定向初次输出](anchor-tests.txt)，获准目录权限后[4项定向测试](anchor-tests-final.txt)通过。
- 第一轮真实记忆测试发现“报销所需提交材料”被误当事实，业务答案保留、memory_valid=false。原记录在[runs/memory](runs/memory/summary.json)，没有删掉。增加名词性关注事项正例并修正检查，再重新安装，[最终124项测试](offline-tests-repair.txt)全部通过、无跳过，9.175秒；随后全部40轮重新运行，旧40轮不冒称最终源码结果。
- 新链路第一次配置预检缺固定revision，未发起模型请求，见[失败说明](anchor-reload-preflight-failure.json)。脚本加入与既有评估入口一致的显式权重/revision参数后使用新目录重跑，未修改私人.env。

## 真实回归与实际输入

新增链路运行前保存[预期](runs/anchor-final/pre-run-expectations.json)。隔离D02从15天改45天，并在可读取正文明确2026-03-01起替代D01提交期限；冻结任务日期2026-10-29，不按较新日期自行裁决，不覆盖基础data/knowledge.json。

| 最终组 | 轮数 | 实际证据 |
| --- | ---: | --- |
| 核心六类各两次 | 18 | [core-final](runs/core-final/summary.json)，含住房补贴、天气、完整两轮与临时/持续read故障 |
| 规则与部分结果 | 9 | [regressions-final](runs/regressions-final/summary.json)，含单D01/加入D02、生效前后、混合状态、用户偏好和4K替换 |
| 记忆语义 | 7 | [memory-final](runs/memory-final/summary.json)，跨窗、换题、纠正、1080p旧历史下重载4K |
| 既有授权资料实验重放 | 2 | [personal-final](runs/personal-final/summary.json)，重放先前独立代理提出的MOV→WEBM预期；本次由主代理执行重放，不冒称新独立提案或用户亲自操作 |
| 新锚点连续追问 | 2 | [fresh第一轮](runs/anchor-final/fresh-t1.json)、[第二轮](runs/anchor-final/fresh-t2.json) |
| 旧污染锚点连续追问 | 2 | [legacy第一轮](runs/anchor-final/legacy-t1.json)、[第二轮](runs/anchor-final/legacy-t2.json)、[明确标注的历史注入fixture](runs/anchor-final/legacy-fixture.json) |

新链路两条路径均保留同会话原历史，第一轮查双方及补查后待澄清；隔离修改、显式重载后第二轮重新读取D02，回答45天并引用明确替代正文。legacy路径通过SQLite测试fixture注入原失败内容，消息来源映射到本会话，不伪称是新模型生成；重开仓储后该旧锚点失效，传入模型的系统锚点为null。每轮文件的actual_model_inputs保存实际传给模型的完整消息（含历史选取、锚点与工具观察），不包含认证头、真实密钥或内部思维。

实际执行（需本地密钥，会产生费用；语料为公开虚构资料）：

```powershell
.venv/Scripts/python.exe -I examples/batch-11/run_anchor_reload.py --live --env-file .env --weights models/bge-small-zh-v1.5 --revision 7999e1d3359715c523056ef9478215996d62a620 --output examples/batch-11/runs/anchor-final
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output examples/batch-11/runs/core-final
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group regressions --output examples/batch-11/runs/regressions-final
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group memory --output examples/batch-11/runs/memory-final
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group personal --cases-file examples/batch-8/personal/cases.json --output examples/batch-11/runs/personal-final
.venv/Scripts/python.exe -I examples/batch-11/audit_evidence.py --output .cache/batch11-audit-new.json
```

输出目录/报告文件必须尚不存在，复跑使用新名称，不能覆盖本次证据。原批次日期、模型温度0和真实BGE固定revision等配置均在metadata/Trace中；不保证确定性或统计稳定性。每个评估过程有5元已知usage估算停止阈值，不是账户余额或未知usage的费用上限。

## 当前版本、矩阵与费用

[79场景矩阵](acceptance-matrix.md)、[结构化索引](acceptance-matrix.json)覆盖既有74项及新增5项。本批最终40轮的全部运行模块指纹与当前安装包/src一致，引用来自本轮read-set及对应快照，见[审计索引](evidence-index.json)。第八、九、十批文件保留其历史版本；未改动的检索实现与依赖可复用原独立环境证据，不将旧环境记录改称本批新源码的冷启动。共享提示/记忆受影响的真实业务已全部重跑。

本批两轮尝试合计80个独立任务，已知usage保守估算**2.961010元**，未知usage0；最终40轮1.481390元是其中子集，不再相加。此前已知估算子集3.376858元与本批相加为6.337868元；历史第三批首次失败usage未知，所以全项目总估算及实际账单仍未知。未查询余额或宣称30元预算已对账。没有把模型耗时或代理工作计为个人工时。

用户已经补充约12小时阶段性投入及架构/loop/记忆的理解范围，见docs/04、05；具体个人学习前后变化的例子仍可补充，本批不代编。锚点技术修复是否满足本批固定验收场景，以独立审查结论为准，不以规划勾选或机械checks替代。

## Standards（当前审查状态）

独立只读代理batch11_standards对基线e1e9ef2后的非空候选进行规范与工程审查，首次发现1项P2：合法议题前缀会使同字段后附的旧结论绕过检查。修复冒号/连接词分句、收紧议题豁免范围并增加无分隔符组合反例后，代理对当前安装包独立验证36个允许项、42个拒绝项，原P2已闭环，当前已审查代码0项待修问题。最终候选和完整新源码证据仍需在外部余额恢复、回归补齐后再核对；不据此提前完成11.6。

## Spec（当前审查状态）

独立只读代理batch11_spec已逐项审阅前一源码版本的完整40轮与60引用，对当时样本未保留语义问题；这份审阅对应*-final目录。随后规范审查修复改变memory.py，最终*-validated源码必须另行验证，不能将此前40轮审阅转称当前全部通过。当前新源码31轮记录中含2次HTTP402，覆盖未补齐，11.5/11.6保持未完成；没有恢复最终通过结论。
