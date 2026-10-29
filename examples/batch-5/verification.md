# 第五批实际验证

日期：2026-10-29（America/New_York）。范围为5.1–5.4；基线提交`e303cbbf3207cfd690f8a47aa8c6093a8de4f5c5`。AI实现与运行，未记录用户亲自执行或检查引用。没有真实生成模型调用，生成费用0元；真实业务、会话与记忆验收仍待后续任务。

## 环境与实际命令

沿用项目隔离`.venv`（CPython 3.12.13），保留embedding依赖。源码通过非editable安装后执行，不用全局Python或PYTHONPATH。

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache/uv'
uv sync --offline --locked --extra embedding --no-editable --python .venv/Scripts/python.exe --reinstall-package enterprise-knowledge-qa
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
openspec validate enterprise-knowledge-qa --strict
```

实际结果：86项离线测试通过，见[完整报告](offline-tests.txt)；OpenSpec严格校验通过。规划文件按既有规则仅在本地保存，公开仓库的验收依据见docs/01–03和本目录预期。测试使用真实本地快照、读取、BM25/RRF与Mock编码；不加载真实BGE、不访问DeepSeek，不能证明真实模型理解或冲突查证能力。

## 实际输出与检查

下列JSON由实际执行器运行生成，模型动作是受控Mock；文件内包含输入、输出、canonical引用、read-set、日期时区、计数和完整Trace。测试宿主日期用于这些Mock输出；不是服务历史日期查询功能。

| 记录 | 实际结果 | 检查 |
| --- | --- | --- |
| [正常结束](answered.json) | answered | 本轮原文读取后回填引用 |
| [材料+冲突](needs_clarification.json) | needs_clarification | 保留材料和期限双方引用、缺口及单个依据请求 |
| [材料+资料缺失](insufficient_evidence.json) | insufficient_evidence | 保留材料，不把资料缺失写成事实不存在 |
| [材料+天气](out_of_scope.json) | out_of_scope | 保留材料及天气边界 |
| [执行中断](interrupted.json) | incomplete | 已读证据保留，执行问题单列，不追加模型收尾 |

新增8项测试覆盖独立引用错误（未知、未读、跨指纹、伪原文、重复和非法标记）、逐字出处回填、格式修正独立计数、所有混合优先级对、部分结果、缺口/追问结构和中断证据。另验证合法回答后Trace保存超时仍保留已验证内容；已有上限/恢复/超时测试一并通过。按问题判定事实、冲突消解、是否应补查及追问语义均由模型承担；程序不硬编码业务数字。

固定语义预期见[expectations.json](expectations.json)。它们是未来真实模型评估的预期；本批并未真实执行这15个语义场景，不将受控动作日志描述为真实决策。引用合法性和语义支持性分别判断，详见docs/03新增规则。

## 失败、修复与复跑

- 初次引用测试读取了旧的已安装包，导致新字段和标记检查未生效；按README重新构建安装后3项引用测试通过。
- 默认uv缓存无法写入，改用项目`.cache/uv`；联网构建依赖获取出现重试，改用已有声明依赖的离线构建成功，没有新增依赖或更换版本。
- 首次全量85项有1项测试夹具失败：空字典状态被测试辅助函数的默认逻辑替换，未真正送出非法状态。改成非空非法对象后85项全通过；业务校验未为此放宽。

## 限制与审查

程序不证明标记旁的所有语句都获得语义支持，也不证明模型已找到全部冲突；part_statuses不能独立证明没有遗漏问题。单字符串加问号数量检查不能识别所有自然语言多重追问，必须配合指令和真实语义核查。锚点提议仍明确未校验、未持久化。

源码与测试文件的最终指纹见[source-fingerprints.json](source-fingerprints.json)，使用UTF-8/LF归一化SHA-256，便于在不同Git换行设置下复核；个人工时未推算。

按code-review技能从本批开始基线对候选改动进行两个独立只读代理审查（提交前暂存diff，非空；基线后尚无提交）：

- Standards：0项可行动问题；无额外AGENTS.md或独立编码规范，按项目文档约定和技能smell baseline核查。
- Spec：初次1项P3，固定追问预期使用未确认简称“星剪”，会混入未确认别名识别要求；已改回需求和资料的正式名称“星帆剪辑”，代理复核确认解决。其余未发现本批缺失、错误实现或范围扩张，新增保存超时测试也已审查。

最终待修问题：Standards 0，Spec 0。最新86项测试通过；审查后仅修正上述用例文字和记录，不更改业务实现。仓库没有docs/agents/issue-tracker.md，本次直接使用用户指定OpenSpec与docs/01作为规格来源，无需查询issue；以后如需该技能的issue跟踪工作流，可运行`/setup-matt-pocock-skills`。
