# 综合验收与仓库交付（题号3）

交付仓库：[ShiriZhang/xiaoying-ai-agent](https://github.com/ShiriZhang/xiaoying-ai-agent)，分支`main`。GitHub连接器本轮读取仓库元信息确认`visibility=public`、未归档，见[实际元信息](repository.json)。公开仓库无需指定私有评审账号，可由评审直接读取；未更改仓库可见性或授权其他账号。

本轮验收基线为`3fc7e673692ff155e8f64c653160f3a9aa92edfc`。提交前审查本批文档和审计脚本候选；最终交付SHA在提交并核对远端后给出，不将提交自身SHA写回同一提交。检出交付版本后用`git rev-parse HEAD`取得完整SHA，可在仓库`/commit/<SHA>`定位内容。最终提交只补齐综合验收、贡献/复盘与交付入口，业务`src/`、测试、依赖和基础语料未改变。

## 10.1：逐场景综合验收

重新读取提案、设计、任务及五份能力规格。共35项Requirement、74个Scenario：执行17、会话14、回答16、检索12、复现评估15。逐项对照用例、测试、实际记录和交付文件，见[可读矩阵](acceptance-matrix.md)及[结构化矩阵](acceptance-matrix.json)。[规格覆盖核对](spec-coverage.json)逐项比对本地五份规格与矩阵的Requirement/Scenario顺序及名称，74项全部一致；[本地链接核对](local-links.json)最终实际检查359个交付文档链接，无缺失。矩阵中的“结论”是本轮证据核查结论，不预填新的模型输出。

实际执行：

```powershell
$env:QA_MODE = 'mock'
$env:DEEPSEEK_API_KEY = ''
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
openspec validate enterprise-knowledge-qa --strict
.venv/Scripts/python.exe -I examples/batch-10/audit_delivery.py --output .cache/delivery-audit-new.json
```

[120项工程/API测试](offline-tests.txt)全部通过，0失败、0错误、0跳过，实测6.871秒。[OpenSpec严格校验](openspec-validation.txt)通过；这只证明规划结构有效，不冒充业务通过。本轮无新增真实模型调用，不为同一未改动业务源码重复制造付费验收；真实层采用以下已实际运行、指纹与最终源码一致的记录：

- [核心六类各两次及语义审阅](../batch-8/delegated-audit/validated-review.md)：最终四组36任务/121模型尝试，核心含住房补贴、天气、完整两轮和临时/持续工具错误。审阅者为用户明确授权的独立AI代理，非用户本人。语义结论、原文引用及实际动作逐条核对；incomplete故障结果按预期中断核查，不算已回答。
- [规则与记忆变体](../batch-8/verification.md)：单D01、加入D02冲突、有效替代/未来生效、部分结果、正文替换、跨窗、换题、纠正、旧结论不复用；独立代理先提MOV→WEBM预期再重载运行。保留原失败和全部104轮尝试，不把名为final的早期失败目录当最终通过。
- [第九批冷启动](../batch-9/verification.md)：两个干净副本新venv、无全局包继承，空缓存无密钥Mock各120测试/13次HTTP及PowerShell，外部网络阻断。另显式独立下载固定revision的6文件权重，真实BGE14项候选及重载边界通过，真实HTTP最小问答3模型/2工具通过。
- 执行上限、一次恢复、一次格式修正、单次/总deadline、容量/存储/锚点失效等工程故障，由本轮实际通过测试逐项覆盖；模型首次失联等历史真实失败亦保留。不强行制造不可达第8模型请求。

[交付审计](delivery-audit.json)再次核对当前安装包、工作区src、第八批四组运行时指纹、第九批两空环境与真实HTTP指纹一致；前批56项验证输入文件指纹未变。核查最终36任务全部canonical引用与各自资料快照、本轮read-set、ID/日期/出处一致。机械存在性检查不替代已链接的独立语义审阅。全部必需场景已有实际结论，当前没有因真实层未运行而悬空的验收项。

## 10.2：文件与发布核查

已确认本地Git及既有`origin=https://github.com/ShiriZhang/xiaoying-ai-agent.git`，未新建其他仓库。用户本轮明确授权本批code review通过后commit并push；审查基线固定为上述SHA，提交后核对远端`refs/heads/main`与本地HEAD一致。

文件清单包含README、src、tests、data、examples、docs/01–05、pyproject.toml、uv.lock及.env.example。本批更新五份文档当前状态与AI/个人贡献边界，保留历史批次的失败及阶段记录；data/README修正旧“未实现”描述。OpenSpec和本地技能仍按既有规则保留本地，不发布；未归档change或同步主规格。

审计实际候选文件：无.env、私钥、模型权重、venv、缓存、SQLite、runtime数据库/日志进入提交；精选examples仅含虚构资料、演示问题和脱敏证据。以本地实际配置密钥作精确内容排查并检查常见密钥/私钥形态，不输出真实值；报告记录是否有本地密钥可用于核查及是否命中，不声称静态扫描能识别任意未知秘密。`.gitignore`实际匹配测试亦通过。

## 10.3：提交定位、费用及限制

题号为**3**，仓库URL见文首，最终SHA在交付消息及该版本Git历史中定位。本批不改变业务源码/依赖，所以第八、九批实际报告继续对应最终源文件指纹；不能用较早整体commit不同来否认相同源码，也不将旧失败改写为最终成功。

已知usage保守估算子集：第三批两次成功0.016614元、第八批全部104轮3.333384元、第九批最小问答0.026860元，合计**3.376858元**。第三批首次失败usage未知，因此全项目总费用和实际账单仍未知；未查询账单、余额或宣称30元预算已对账。第十批没有新付费模型请求。用户个人主动工时未提供；AI操作、代理审阅与模型耗时不计作个人工时，也不补造个人学习经历。

实际限制：仅验证Windows x86-64/CPython3.12.13；单机单进程演示，无身份权限、多进程协调或部署；Mock为有限受控策略，不证明语义能力；两次核心重复及有限固定样本不保证统计稳定性或泛化。Reranker和对照实验为可选项未做；这些范围边界不被改写成必交已完成能力。必交实现及证据无已知未完成项，提交发布以最终远端核对为准。

## Standards

独立只读代理`batch10_standards`按code-review技能审查非空候选`git diff --cached 3fc7e673692ff155e8f64c653160f3a9aa92edfc`，用户要求先审查再提交，故基线后commit列表为空。对照README、docs/01–05、依赖声明及技能smell baseline，0项可行动问题，无最严重待修项。审计脚本与用途相称，未发现需要拆分或抽象的明显异味；文档保留历史、分层验证及未知费用/工时边界，密钥扫描不输出真实值。按建议在审查记录写入后再做最终候选扫描。

## Spec

另一独立只读代理`batch10_spec`对照10.1–10.3及五份能力规格审查同一候选，0项可行动问题，无待修项。核对74场景、120测试、严格校验、最终36轮引用、两个冷启动和前批56项指纹；独立运行审计函数亦通过。公开仓库、题号、交付清单及提交定位说明符合要求。发布与最终SHA核对按既定顺序留在审查后执行。

两轴均0项发现。审查后仅补充审查记录、更新增加链接后的核对数量并生成[最终候选审计](delivery-audit-final.json)，没有业务代码或依赖变更。初次审计按执行时的文件数量记录，原报告保留；最终候选另核查，不覆盖原始结果。
