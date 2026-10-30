# 第十一批：验收后锚点内容边界修复

本批修复、真实回归与两轴独立审查已完成，通过后按用户授权提交发布。对应11.1–11.6，基线为`e1e9ef2cd5376afd68aea7b38c36c755d2dbbfcc`。最终源码的124项测试、实际Mock HTTP/重启及40轮真实回归均有实际记录；当前验收以本页及新审计为准。个人学习前后变化的具体例子仍可补充，不冒称所有笔试材料无保留通过。

## 修复内容与边界

保持subject/focus/pending_clarification三个字段、同次finish、8/6预算、一次恢复/修正及业务/记忆失败隔离。没有新增记忆模型调用、工具、数据库字段或普通用户故障参数。

agent系统指令加入全部字段正反例；memory.validate_anchor对结构/来源之外可识别的陈述形态做有限检查；SessionStore.get_session在旧数据库快照再次使用前重检。新锚点非法时保留合法业务结果、拒绝快照并告警；旧污染快照不注入下一轮系统锚点，原历史仍保留，begin_run按原机制先持久失效旧锚点。

允许“差旅报销／提交期限／待确认适用制度”“1080p导出支持情况”等讨论事项或用户问题；禁止将已读资料结论放进任一锚点字段。不以数字黑名单删除用户问题。检查不是通用语义分类器：新措辞仍可能漏判或误判，结构、来源或正则通过不能证明任意自然语言都符合边界；真实生成仍须另行语义审阅。

## 原失败与修复过程

- [两份原始失败索引](baseline-failures.json)记录原有效/已保存锚点、文件SHA-256和旧校验器实际接受结果；[正反例](anchor-cases.json)固化预期。原文件未改动，测试直接读取它们验证新校验拒绝。
- 首次重装受网络及Windows临时目录权限影响；使用已声明依赖的本地缓存与获准临时目录操作后成功，依赖声明未变。[首次124测试](offline-tests-initial.txt)中新增SQLite测试未关闭连接导致清理失败，修正为显式关闭；另一次受限运行失败保存在[定向原输出](anchor-tests.txt)，[定向复跑](anchor-tests-final.txt)通过。
- 第一轮真实记忆回归将合法关注事项“报销所需提交材料”误判为结论，业务答案保留而记忆降级。原记录在[runs/memory](runs/memory/summary.json)。补充名词性事项正例后完整40轮复跑，旧目录未覆盖。
- 独立规范审查发现P2：`待确认适用制度：15天与30天规定冲突`会整体获得议题豁免。修复冒号/连接词分句、收紧豁免范围，并补充无分隔符拼接反例；三个字段共36个允许项、42个拒绝项经独立代理复核符合预期。
- 新链路第一次缺显式权重revision，在付费调用前配置失败，见[预检失败](anchor-reload-preflight-failure.json)；验证入口加入明确权重/revision参数，未修改私人.env。
- 修复后的真实回归遭遇HTTP402，脚本停止且未自动重试；用户随后明确回复“已处理余额，可以继续验证”。核心/规则在新目录完整复跑，不覆盖原失败。中断时[未完成审计](evidence-index-incomplete.json)、[暂停状态](pause-status.json)及[阶段报告](verification-before-resume.md)原样保留，不将它们改写为通过。

## 当前实际验证

| 检查 | 结果与证据 |
| --- | --- |
| 离线工程/API测试 | [124项全部通过](offline-tests-release.txt)，0失败/错误/跳过，7.239秒 |
| 实际Mock服务与README请求 | [13次HTTP](http-validated.json)、[PowerShell](powershell-validated.json)，两轮、会话隔离和进程重启通过；外部网络/BGE访问被阻断 |
| 核心六类各两次 | [core-resumed](runs/core-resumed/summary.json)，18轮，含住房补贴、天气、完整两轮及临时/持续read故障 |
| 规则/部分结果 | [regressions-resumed](runs/regressions-resumed/summary.json)，9轮，含单D01/加入D02、已/未生效、混合状态、用户偏好及4K替换 |
| 记忆语义 | [memory-validated](runs/memory-validated/summary.json)，7轮，跨窗、换题/纠正及旧1080p历史下重载4K |
| 既有授权资料实验重放 | [personal-validated](runs/personal-validated/summary.json)，2轮，MOV→WEBM；本次由主代理重放既有独立代理预期，不冒称新独立提案或用户亲自操作 |
| 新旧锚点连续追问 | [anchor-validated](runs/anchor-validated/summary.json)，4轮，两条完整真实链路 |
| 当前版本及全部费用记录 | [恢复后严格审计](evidence-index-resumed.json)，最终40轮模块指纹与安装包/src一致，原失败SHA未变；引用匹配本轮read-set及各自快照 |
| 规划校验 | [OpenSpec严格校验](openspec-validation.txt)通过，仅证明规划结构有效 |

新链路先保存[运行前预期](runs/anchor-validated/pre-run-expectations.json)，第一轮真实读取期限双方、补查后待澄清。隔离D02从15天改45天，并以正文明确自2026-03-01起替代D01提交期限，冻结任务日期2026-10-29，显式重载后同会话追问“那现在应该按哪个？”。正常路径和[历史污染fixture路径](runs/anchor-validated/legacy-fixture.json)均重新读取新D02、答45天并引用替代原文。

[fresh第一轮](runs/anchor-validated/fresh-t1.json)、[fresh第二轮](runs/anchor-validated/fresh-t2.json)、[legacy第一轮](runs/anchor-validated/legacy-t1.json)、[legacy第二轮](runs/anchor-validated/legacy-t2.json)保存实际模型输入、完整历史选取、锚点前后、动作、引用及usage。legacy注入被明确标为历史测试fixture，来源映射到本会话，非新模型输出；重开仓储后系统锚点为null，原业务历史保留。不保存密钥、认证头或内部思维。

## 复跑入口及证据版本

```powershell
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-11/run_anchor_reload.py --live --env-file .env --weights models/bge-small-zh-v1.5 --revision 7999e1d3359715c523056ef9478215996d62a620 --output .cache/anchor-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output .cache/core-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group regressions --output .cache/regressions-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group memory --output .cache/memory-new
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group personal --cases-file examples/batch-8/personal/cases.json --output .cache/personal-new
.venv/Scripts/python.exe -I examples/batch-11/audit_evidence.py --output .cache/batch11-audit-new.json
```

付费入口需显式--live，仅用公开合成资料及隔离副本；输出目录/文件必须尚不存在，复跑换新名称。每组5元已知usage估算阈值不代表余额、账单或未知usage费用上限。模型temperature=0、BGE固定revision、日期与精确配置均在metadata/Trace中，不保证确定性或统计稳定性。账单与个人时间不从模型耗时推算。

[79场景矩阵](acceptance-matrix.md)及[结构化索引](acceptance-matrix.json)已将受影响真实业务链接到当前五组40轮。旧第八、九、十批报告保留其源码和独立环境版本，不改成新源码的冷启动证明。此前*-final目录属于审查修复前版本；core/regressions-validated有402中断，当前应看resumed两组。仅未改动检索实现/依赖等证据复用原版本并说明范围，不拿旧模型结果代替新源码验收。

## 费用、贡献与交付范围

本批全部138个独立任务、474次模型尝试，已知usage保守估算**5.043826元**，另有2次402请求usage未知；最终40轮已知估算1.461346元是其中子集，不能再相加。与此前已知子集3.376858元相加为8.420684元；历史第三批及本批均有未知用量，全项目总额和实际账单仍未知，未查询余额或宣称30元预算已对账。

个人约12小时阶段性投入及架构/loop/记忆理解按用户原话保留；具体学习前后变化例子仍可补充，不由AI代造。本批技术修复完成与个人笔试材料是否无保留齐全分别说明。提交按用户授权在最终审查后执行，最终SHA与远端核对在交付消息及本地交付记录给出，不将提交自己的SHA写回同一提交。OpenSpec仍仅本地保留，未归档change。

## Standards

独立只读代理batch11_standards按code-review技能审查非空暂存候选`git diff --cached e1e9ef2cd5376afd68aea7b38c36c755d2dbbfcc`，基线后commit列表为空，遵循用户先审查后提交的顺序。首次P2议题豁免绕过已修复；代理独立验证三个字段36允许项与42拒绝项，再复核最终生产代码无回退、五组40轮指纹一致。独立重算138任务/474模型尝试、已知估算5.043826元及2次未知usage，与记录一致。最终0项可行动问题，无最严重待修项。

## Spec

另一独立只读代理batch11_spec对照11.1–11.6与五份能力规格，重新阅读当前core-resumed18、regressions-resumed9、memory-validated7、personal-validated2、anchor-validated4，共40轮实际答案、缺口、动作及按字段名核对的有效锚点。65处引用与各自快照、本轮read-set、出处和版本一致，未发现擅自裁决冲突或有效锚点携带企业结论。legacy第二轮所有实际模型请求的系统锚点为null，原历史保留；两路径均按新45天及明确替代正文回答并清空待澄清项。独立审阅结果见[本批最终语义审阅](independent-semantic-review.json)。最终0项可行动问题，无最严重待修项。

两轴均通过；原402、原失败和旧版审阅保留其版本。审查后仅补充审查记录与文件检查，不改变业务源码或依赖。最终候选的[文件、链接与密钥检查](delivery-check-release.json)通过；静态排查仅覆盖配置密钥及所列文件类别，不宣称能识别任意未知秘密。
