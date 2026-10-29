# 第八批真实验证与证据

日期：2026-10-29（America/New_York）。实施基线`4e35fcb950456a4eda39f81b47cef1a3f3d95427`。范围8.1–8.6；第9批全新环境和第10批综合交付仍独立验收。

## 授权与执行者

本批先向用户请求亲自提出资料修改及工时；用户明确回复：

> 我授权你使用一个单独的智能体（和当前编写代码的智能体不同的另一个智能体）来完成这次资料修改

> 我授权你使用另外一个智能体帮我操作

据此修订本地proposal/design/能力规格/tasks和公开docs/01：独立于主实现代理的资料代理先提出D09修改及预期，再真实运行核查；另一个证据代理独立审阅结论/引用、动作、记忆和费用。全部明确为AI代理代办，不记作用户亲自操作，不把代理时间计为个人工时。没有账单访问或用户个人工时记录，账单为null、个人主动工时未记录。

## 输入、环境与实际执行

[cases.json](cases.json)在首次运行前保存输入、预期、场景映射；每次运行另存不可覆盖的pre-run-cases.json。A03拆住房补贴/天气，A06拆临时/持续read故障，A05保留完整两轮。固定数值只存在于合成资料、预期或断言，回答代码不根据问题硬编码制度结论。

运行使用已安装的隔离CPython 3.12.13、官方deepseek-flash非思考模式和真实本地CPU BAAI/bge-small-zh-v1.5。个人.env缺少embedding revision，因此验证命令显式使用已准备权重及锁定revision，不改个人.env。每个metadata.json记录实际运行平台、包版本、请求模型、revision、基线SHA与实际已安装运行模块的内容指纹；每个结果记录响应实际模型标识、日期/时区、资料指纹、原文、usage、动作/观察/计数、锚点和历史选取。

```powershell
# 每次output必须为新目录，失败和原始结果不覆盖。
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output examples/batch-8/runs/core-validated
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group regressions --output examples/batch-8/runs/regressions-validated
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group memory --output examples/batch-8/runs/memory-validated
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group personal --cases-file examples/batch-8/personal/cases.json --output examples/batch-8/runs/personal-validated
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-8/inventory.py
```

上列目录已经存在，是实际运行记录；复现请使用新目录名。--live显式授权该次付费验证。默认单次运行的已知usage估算guard为5元，不等于账户余额或未知用量上限；本批实际总量另行去重汇总。执行日期冻结、历史预算1和工具故障仅是内部验证输入，不暴露为员工API参数。

## 最终版本证据入口

| 最终组 | 实际轮次 / 模型尝试 | 已知保守估算（元） | 覆盖 |
| --- | --- | --- | --- |
| [core-validated](runs/core-validated/summary.json) | 18 / 58 | 0.574484 | 六类各独立两次，含A03和A06双子场景、两次完整两轮追问 |
| [regressions-validated](runs/regressions-validated/summary.json) | 9 / 36 | 0.380280 | 单D01/加入D02、生效/未来日期、三类部分结果、用户偏好、4K正文 |
| [memory-validated](runs/memory-validated/summary.json) | 7 / 21 | 0.197146 | 跨窗对象、换题、纠正、旧1080p历史与4K新正文 |
| [personal-validated](runs/personal-validated/summary.json) | 2 / 6 | 0.056706 | 独立代理预先提出MOV→WEBM，隔离重载，同会话核查新引用 |
| 最终四组小计 | 36 / 121 | 1.208616 | 未知usage 0；不是统计稳定性或泛化保证 |

每个组的summary.json指向每轮独立JSON；corpora目录保存该指纹实际完整语料。所有组内机械checks只检查状态、来源、计数等，不自动判定语义通过。独立证据代理已逐条阅读并核对最终36轮，见[完整逐项矩阵](delegated-audit/validated-review.md)，确认四组全部运行时源码指纹一致且符合固定预期；持续故障的通过预期为incomplete而非“回答成功”。个别材料回复附有D04支持的流程说明，未再发布未核实期限。个人组另有[运行前预期](personal/proposal-before-run.md)、[独立核查](personal/result-review.md)和[离线复核脚本](personal/verify_personal.py)。

## 失败、修复与复跑链

1. [core-initial](runs/core-initial/summary.json)：18轮、61模型尝试，4轮失败（冲突两次、住房补贴一次、临时故障一次）。引用marker裸C1而非[C1]、clarification打包多个问号导致一次修正仍失败。被拒候选还包含没有依据的“临时从严”期限建议；失败原文及格式反馈保留。独立审阅见[初跑报告](delegated-audit/core-initial-review.md)。
2. [core-repair-1](runs/core-repair-1/summary.json)：补充marker schema、具体修正反馈、单问及禁止临时选边指令后，机械格式改善，但材料答案两次顺带发布不同的单侧期限；冲突补查后未读新候选。未据状态成功就判通过，见[第一轮修复审阅](delegated-audit/core-repair-1-review.md)。
3. [core-final](runs/core-final/summary.json)与[regressions-final](runs/regressions-final/summary.json)：进一步约束只答所问、候选暴露矛盾时必须双侧核查，显式temperature=0。主要结论改善，仍存在冲突补查只search不read新候选；目录名final是当时命名，不能当作最终通过，见[补查修复前审阅](delegated-audit/pre-guidance-review.md)。
4. 增加通用任务证据状态：search观察列出本任务已读及未读候选；已读后补查出现新候选时，在邻近系统上下文中标明“程序证据状态”，提醒读取新相关原文，Trace保存evidence_guidance。程序不选工具、不生成制度结论、不按数值裁决，不自动执行额外工具。先做[定向真实检查](runs/conflict-guidance-check/summary.json)，再运行上表最终四组。
5. 最终冲突路径实际为search→read双方→补查search→read新相关D03/D04→finish，5模型/4工具；没有新文档的仅D01/D02隔离库不虚构第三份材料。充分材料通常3模型/2工具，天气1模型/0工具；临时失败由真实模型选一次恢复后成功，持续失败一次恢复再错即停，无额外收尾。查询调整和动作差异来自真实Trace，不预设完整流程。

最终temperature=0只用于减少采样漂移，不保证确定性；仍严格拒绝多动作和非法引用。两次核心重复是有限样本，不能宣称普适最优或稳定成功率。新增回归测试覆盖具体反馈、已读/未读状态不授予引用权及费用去重；[120项离线测试](offline-tests.txt)通过，不用其替代真实语义核查。

## 全部尝试、费用与工时

[evidence-index.json](evidence-index.json)按顶层request_id去重，仅计顶层model_response/model_error usage，忽略嵌套历史、复制和滚动progress快照。**全部11组、104个任务、343次模型尝试，已知保守估算3.333384元，未知usage 0**；包括所有失败和个人组三次运行，不只计最终成功组。最终四组1.208616元是其中子集，不与全量再相加。

估算沿用[2026-10-29官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)的Flash高峰未缓存输入2元/百万、输出8元/百万，故保守忽略缓存和空闲折扣；实际账单未核实、invoice_cny=null，不推断账户余额或“剩余30元”。显式temperature参数符合[官方Chat Completions契约](https://api-docs.deepseek.com/api/create-chat-completion/)。没有使用未公开的并行调用参数来隐藏多动作错误。

主代理未全程计量主动工时，不能从模型耗时倒推；每轮elapsed_seconds是任务运行耗时，summary elapsed是评估循环耗时（不含此前BGE初始化），并发组不能直接相加为人类工时。资料代理记录了自己的观察窗（含等待），明确非个人主动工时。用户个人工时未提供，不填0或18小时。

## 状态与后续

基础data/knowledge.json保持审阅版；所有变更位于隔离临时副本，实际快照随证据保存。公开文档如实记录独立代理授权，不冒称人类完成。120项离线测试与OpenSpec严格校验通过；[56项最终文件指纹](source-fingerprints.json)采用UTF-8去BOM、LF归一化SHA-256，最终四组全部运行模块指纹一致且与当前src相符。[39项安装包版本](environment-packages.json)兼容检查通过，精确配置密钥扫描未发现密钥进入源码/文档/证据。第9批冷启动与第10批最终交付未完成，当前任务40/46。

## Standards

独立只读代理按code-review技能审查非空暂存候选`git diff --cached 4e35fcb`。用户要求先审查后提交，当时基线后commit列表为空。对照README、docs/01–03、依赖声明和技能smell baseline，0项可行动规范问题或需修改的判断性异味。新增提示没有授予引用权限、自动执行工具或改变预算，费用去重和历史失败记录正确保留。

## Spec

另一独立只读代理对照8.1–8.6及相关能力规格、输入预期、源码和实际证据，0项可行动问题。定向复核最终36轮全部引用属于本轮read-set、正文与快照一致，四组运行时指纹与当前src一致；冲突补查读取、持续故障停止、跨窗历史省略、换题/纠正、1080p→4K及MOV→WEBM均核查。用户授权的代理代办如实归属，未冒称人类操作、真实账单或第9/10批完成。

最终两轴均0项发现，无最严重待修项。审查后仅补充审查记录，业务源码未改变，无新增付费调用。
