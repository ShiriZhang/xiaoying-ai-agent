# 方案设计

第十一批最新状态：锚点修复及最终源码40轮回归已完成，124项测试和实际HTTP通过，两轴独立审查通过。79场景及全部失败/恢复记录见[当前修复报告](../examples/batch-11/verification.md)。下面80任务、111任务、50/52及此前费用数字按当时阶段保留，不是当前未完成状态；最新累计以本批恢复后审计为准。个人12小时估算及架构理解归属不变，具体学习收获例子仍可补充。



最终实现导航：四路由、原生执行器、混合检索、canonical引用、SQLite与三字段锚点均已实施；真实效果与全新环境验证分别见第八、九批，综合74场景核查见[交付记录](../examples/batch-10/verification.md)。下文按批次保留演进过程，早期“待实现”描述对应当时状态，以本段及后续实际记录为准。本批没有修改业务源码或依赖。

第八批实际更新：真实评估发现并修复了引用标记反馈不具体、多追问、顺带发布未核实规则、补查未读新候选等问题。finish的marker schema明确方括号，反馈给出格式示例；指令只答所问、禁止以临时/从严建议裁决冲突。真实适配显式temperature=0，并在结果记录；不保证确定性。search观察新增任务read-set和未读候选，已读后的补查有新候选时补充邻近系统证据状态，Trace保存evidence_guidance。它不执行工具或生成制度结论，模型仍选下一动作，8/6预算和一次修正/恢复不变。完整失败与复跑见[第八批记录](../examples/batch-8/verification.md)。

第七批实际更新：四个FastAPI路由、本地单进程启动器和受控Mock演示已接通。当前入口和HTTP错误契约见文末“第七批REST接口”；早期“API待实现”为当时状态。实际HTTP/PowerShell请求、重启/隔离及验证边界见[第七批记录](../examples/batch-7/verification.md)，不代表真实语义或全新环境验收。

第六批实际更新：已实现SQLite会话仓储、会话编排、完整轮次历史窗口、同次finish锚点校验和失效降级。下文早期“记忆待实现”描述其当时状态；以文末“第六批会话与上下文”为当前实现契约。HTTP路由仍留第七批，真实记忆语义验收留第八批。

第五批实际更新：已实现业务结果和混合状态校验、完整模型任务指令、canonical引用回填与中断证据保留。当前实现契约和实际Mock输出见文末“第五批结果与引用”；会话/记忆/API和真实业务语义验收仍待后续任务。

第四批实际更新：已实现本地CPU BGE、BM25/RRF混检、原子重载及同一Agent集成。下文早期“检索未接入”的说明是第三批当时边界，现以本节与第四批证据为准。真实生成模型六类验收、会话/API及完整记忆仍未完成。

检索输入选择标题+条文主体，避免每段重复出处头干扰排名；canonical原文和元信息完整保留供读取。中文采用NFKC/casefold、单字/双字混合切分，无外部分词词典；BM25 k1=1.5、b=0.75，IDF=log1p((N-df+0.5)/(df+0.5))保持单D01正分。向量为固定revision BGE的CPU CLS归一化表示，中文查询加检索前缀，512-token长度检查在padding/模型执行前进行，不允许隐式截断。

两路各前12，内存精确余弦相似性与BM25排名通过RRF k=60去重；默认6/可扩大12，稳定同分按片段ID升序。无人工“答案可信度”或日期权威字段，不以语义阈值判断事实真值。检索返回短摘要、出处、两路排名/分数、融合排名/分数和配置，读取才授予本任务原文权限。

`RetrievalStore`把不可变资料快照、词项统计和向量作为一个版本发布。`reload()`完整验证和编码成功后一次替换；失败保留旧版本，旧任务不会看到新索引配旧原文。`create_agent`将取得的同一index用于search与read，Trace写入实际编码器revision/权重指纹/CPU参数。编码失败给工具错误，无仅BM25或Mock降级。实际参数、版本、候选与重载证据见 [第四批验证](../examples/batch-4/verification.md)；可复制的安装/准备/运行步骤见 [README](../README.md)。

状态：当前按用户分批授权实施；工程基础、合成资料、快照与读取已完成，第三批新增模型适配及原生执行约束。下文设计与末尾“第三批实际实现”分开阅读；检索索引、完整业务呈现、会话/记忆与API仍待对应批次。实际验证见 examples/batch-3，不能将组件测试或协议冒烟当作最终业务验收。业务范围及验收以 [01-requirements.md](01-requirements.md) 为准，术语以 [CONTEXT.md](../CONTEXT.md) 为准。

## 结构与职责

- FastAPI：RESTful 接口与输入校验。
- 会话层：SQLite 完整问答与结构化锚点的持久化、会话隔离、重启续接。
- 上下文组装：锚点加近期原始问答，附当前问题、日期、工具定义及本轮观察。
- 单 Agent 原生执行器：调用生成模型、校验动作、执行两类业务工具、传回观察、记录 Trace、执行预算。
- 检索层：本地 BM25 与 embedding 排名、RRF 融合；原文读取及引用回填。
- 模型与向量编码适配：真实模式与显式 Mock 共用执行流程，证据标明模式。

这些是模块职责，不是多个运行时 Agent。不引入额外 Agent 框架、独立向量数据库或部署服务。

## 模型接入

生成模型使用 DeepSeek 官方 deepseek-flash，显式关闭思考。本地 embedding 使用 BAAI/bge-small-zh-v1.5，先用 CPU。一个生成模型加一个向量模型，不新增必交 Reranker。

记录请求模型 ID、响应实际模型标识及 embedding 配置，说明别名可能变化。官方能力不等于本项目已验证效果；真实可达性、兼容性与费用仍待实施核验。

- [DeepSeek 工具调用](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)
- [思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)
- [模型价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)
- [JSON 输出](https://api-docs.deepseek.com/zh-cn/guides/json_mode/)
- [本地 embedding 模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5)

## 动态决策循环

1. 从会话取出合法锚点与近期历史，连同当前问题、服务日期和工具定义交给模型。
2. 模型选择一个动作：检索资料、读取片段或结束本轮。
3. 执行器校验参数、检查预算、执行工具，将实际结果或明确错误作为观察交回。
4. 模型根据观察继续检索、调整查询、读取、恢复或结束。程序不预写结论或用固定分支冒充决策。

| 动作 | 契约 |
| --- | --- |
| 检索资料 | 使用模型生成的查询，返回片段标识、出处、短摘要与排名，允许扩大返回数量 |
| 读取片段 | 按标识读取原文，一次最多 3 个 |
| 结束本轮 | 提交业务结果与完整锚点快照；追问随结果返回，不在 HTTP 请求内等待员工回答 |

前两项是业务工具，结束为控制动作。每次模型响应只选一个动作。具体命名与 schema 细节已委托实施选择验证。

## 资料与检索

- 一个 JSON 资料集，12 个文档条目，三主题各 4 个；每个版本有唯一 ID、标题、主题、版本/生效日期与编号短段落。
- 替代、生效等依据写在正文并与元信息一致。当前规则使用运行当天，测试冻结时钟，记录日期与时区。
- BM25 与本地向量检索各取前 12 个片段，RRF 去重融合后默认返回 6 个，允许扩大至 12 个；向量在内存中比较。
- 候选数量是已同意的初值，召回测试可暴露需要调整之处；不将排名分数当作事实可信度，不用日期排名替代优先依据。
- Agent 在检索动作中组织查询，并据观察决定改写、扩展或拆分，不固定多打一轮改写请求。
- 检索摘要不作为最终引用；完整原文通过读取动作取得。
- 修改资料后重新加载并重建两路索引；不做热更新。
- 中文切分、RRF 常数和具体依赖由实施选择并验证。[RRF 机制](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)

## 证据、冲突和结果表达

- 企业事实每轮重新检索、读取；对话和锚点只用于理解问题。
- 模型选择本轮已读片段，程序回填原文、ID、日期与片段标识，回答用 [C1] 等标记关联。原文是连续逐字内容，模型概括与原文分开。
- 引用来源存在不等于支持结论，语义支持性由评估核查。
- 冲突缺少依据时由模型补充查证；已读原文明示有效替代关系时可解释消解，否则列出双方、缺口和最多一个关键追问。
- 部分可答内容先交付；资料缺失与执行错误分开，不将“未查到”解释为不存在。
- 五种状态和混合优先级以需求文档为准；最终具体字段名、错误码由实施确定。

## RESTful API 与会话

| 路由 | 职责 |
| --- | --- |
| POST /sessions | 创建会话 |
| POST /sessions/{id}/messages | 提交新问题，服务端取历史并执行，返回业务结果与 Trace |
| GET /sessions/{id} | 查看问答记录 |
| GET /health | 查看状态与模式，不调用付费模型 |

SQLite 支持重启续问并隔离会话。对外采用服务端会话，对内执行器接收问题和选定上下文。请求格式或会话标识错误使用 HTTP 错误，进入执行后的结果使用任务状态。本机演示，不做身份权限或多进程协调。

## 短期记忆

锚点仅包含当前讨论对象、关注事项、待澄清事项，各附来源消息标识；没有待澄清项时为空。新话题或明确纠正更新/清除旧值，不永久固定首轮。锚点不是企业事实、引用缓存或员工画像。

同一次结束动作生成业务结果与完整锚点快照，程序校验后保存；无独立记忆请求或工具。完整快照替换而非无条件积累旧值，不额外请求仍增加输出 token 与生成时间。

近期原始历史预算初值为 8000 个估算 token，从新往旧选择完整问答，记录实际选入历史，通过真实 usage 校准。锚点、系统指令、当前问题和本轮工具观察另留空间；当前任务内工具循环不裁断。问题无独立字符上限，不截断当前问题，必要内容无法容纳时明确失败。

业务结果和锚点分别校验：

- 整体不可解析或业务结果不合法，使用最多一次格式修正，仍失败则未完成。
- 只有锚点不合法，保留合法业务结果，拒绝新锚点、停用旧锚点并告警；下一轮暂用近期原始历史，等待合法快照重建。
- 模型失联、超时、上限耗尽或最终格式修正失败而无合法结束动作时，停用旧锚点并记录原因，下一轮仅用近期原始历史重建，不伪称获得更新。SQLite 写入失败单独报告，不伪称已保存。

字段来源、状态更新、窗口选择与记忆降级须测试，来源 ID 合法不等于语义必然正确。

- [短期记忆、裁剪与摘要](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [上下文压缩与结构化笔记](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
- [DeepSeek token 计数说明](https://api-docs.deepseek.com/quick_start/token_usage/)

上述资料用于机制参考，不表示引入对应框架，亦不证明方案已通过测试。

## 执行预算与故障

- 每任务最多 8 次模型决策，包含结束与格式修正；最多 6 次业务工具调用，失败与恢复均计数。
- 预算耗尽而任务未结束时直接构造未完成结果，不追加模型收尾。
- 工具故障恢复最多一次，由模型观察错误后选择重试、改参数或停止；格式修正最多一次，二者分开计数。
- 单次模型请求 60 秒、任务总计 300 秒，均可配置；关闭客户端隐式重试。
- 模型鉴权/服务/超时错误明确未完成，不自动 Mock。真实 embedding 错误交回为检索工具错误，不静默改成仅 BM25。

## 离线 Mock

显式模式模拟生成动作和向量编码，使用确定性测试向量；执行器、BM25、融合、原文读取与真实模式复用。不联网或下载权重，输出和 Trace 标明模式。它仅证明流程与工程行为，不证明真实决策或语义召回。

## Trace、验证与实施细节

Trace 记录输入输出、请求 ID、模式、模型及 embedding 配置、模型实际标识、资料指纹、日期时区、执行预算、每步动作参数与观察摘要、简要依据、后续动作、失败恢复修正和停止原因，不记录内部思维过程。记录耗时、usage 和估算费用，未知信息标明，按账单核对 30 元预算。

真实与 Mock 记录分开，选定证据放 examples/，由 [03-evaluation.md](03-evaluation.md) 引用。三层验证及边界用例已经确认，尚未实施或运行。

纯工程细节可在已定边界内选择、记录、验证，无须逐项再问；不得因此新增模型服务、改业务规则、删验收或改变已确认上限。分批实施由用户另行授权。

## 第三批实际实现与验证入口

- `models.py`：官方 DeepSeek 的标准库HTTP适配器，显式 `thinking.type=disabled`，一次请求、禁止重定向；无SDK依赖或隐式重试。响应只保留工具调用、实际模型标识与usage，丢弃reasoning_content和自由正文。Mock要求显式传入受控策略，无网络和权重访问，不自动降级。
- `agent.py`：真实和Mock共用同一循环。每次响应恰好一个动作；多动作全部拒绝，并按各自真实tool-call ID反馈。search为注入接口，未提供时明确工具错误；当前没有真实混合检索。read复用已实现原文工具，执行前校验1–3个唯一ID，成功且未超时才授予本任务已读权限。
- `actions.py`：search(query,limit=6/12,reason)、read(passage_ids,reason)、finish(status,answer,citation_refs,gaps,clarification,anchor_snapshot,reason)。reason为最多240字符的简要依据，不索取内部思维。finish的机械校验支持一次格式修正，引用需含marker、passage_id、corpus_fingerprint并来自本轮已读原文。完整语义支持、混合问题呈现等任务5未据此提前完成。
- 模型调用发起前计数；失败、结束、修正均计入。工具执行前计数；失败与恢复均计入。首次工具故障进入真实后续观察，由模型选择一次恢复或合法incomplete结束；恢复再次失败或额度用尽即停。格式修正独立只允许一次，不借查询变化重置额度。
- 计数修订：用户已明确确认保留8/6硬上限和第6工具后立即停止；在现有单动作与一次修正规则下第8次不可达，实测第7次合法结束及不追加第8/9次。论证和确认原话见 [计数决定](../examples/batch-3/budget-decision.md)。
- `deadlines.py`：可注入单调时钟与日期时钟；任务日期/时区开始时冻结，deadline不受墙钟改变影响。模型等待为min(60秒,任务剩余时间)，本地工具与保存受300秒总deadline限制。每次工作线程只持有私有消息/试读状态，迟到结果不进入任务read-set或Trace。
- 超时可以及时停止对外等待，但不能强杀底层线程或撤销外部计费。检索适配接口也必须避免外部副作用；没有生产级进程终止保证。Trace先写临时文件，检查deadline后才在支持的Windows平台重命名发布，禁止覆盖已有请求ID；写入失败明确报告，超时不发布迟到文件。
- `tracing.py`：返回/保存请求和会话ID、输入、模式、资料指纹、日期/时区、上限、动作参数、观察、计数、恢复修正停止原因、请求/实际模型、每次usage与耗时。脱敏真实密钥及认证头，不存内部思维。输出包含未加载embedding的配置状态，不伪称已运行向量检索。
- 费用按2026-10-29官方Flash高峰未缓存输入2元/百万token、输出8元/百万token作保守费率估算；记录实际cache hit/miss，但不猜高峰/节假日。未知usage或部分未知时总估算保留null，已知子集单列，账单金额仍待人工核对。参考 [官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，30元预算不等于已核实余额。
- finish保留anchor_snapshot提议，当前明确memory_valid=false并提示第6批校验/持久化待完成，不宣称已保存记忆，也不新增记忆模型调用。

离线执行：`.venv/Scripts/python.exe -I -m unittest discover -s tests -v`。少量真实协议验证入口：`.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.smoke --live --env-file .env --output examples/batch-3/live-smoke`。它显式使用真实生成模型和实际原文读取，独立于尚未准备的embedding；不代表六类最终验收。失败、复跑、用量和实际标识见 [第三批记录](../examples/batch-3/verification.md)。

合成资料目录、关键规则、个人验证分工与工时计划已经确认，见需求文档。用户在 Q56 完成整体复核，确认无合法结束动作时停用旧锚点的规则，设计澄清阶段结束，不因此启动实现。实际账号、权重、兼容性、速度、成功率和费用仍待实施验证，不冒充已知事实。

## 第五批结果与引用

`finish`现在提交`status、part_statuses、answer、citation_refs、gaps、clarification、anchor_snapshot、reason`。`answer`按问题分项，用引用标记关联具体企业结论；`part_statuses`按分项顺序给出状态，整体`status`必须符合`incomplete > needs_clarification > insufficient_evidence > out_of_scope > answered`，不一致使用原有一次格式修正机会。程序只检查枚举与优先级，不能自动判断是否漏掉问题分项或错误分类。

`citation_refs`只接收`marker、passage_id、corpus_fingerprint`；拒绝模型传入的原文字段。执行器核对本任务read-set、片段存在性、快照指纹和`[C1]`格式，拒绝未声明、重复或错误标记，再从不可变快照回填`doc_id、title、version_date、effective_date、text`。`text`是完整连续原文，模型的归纳只在`answer`中。相同标记可在多个受其支持的结论旁重复出现，但引用列表只能定义一次。

以下摘自[实际受控Mock运行](../examples/batch-5/needs_clarification.json)，不是DeepSeek语义验收：

```json
{
  "status": "needs_clarification",
  "part_statuses": ["answered", "needs_clarification"],
  "answer": "材料：发票与出差审批单[C1]。\n期限：D01为30天[C2]，D02为15天[C3]，缺少消解依据。",
  "gaps": ["尚无确认现行期限或替代关系的依据。"],
  "clarification": "能提供现行制度或替代说明吗？"
}
```

核对关系：`[C1] → D03-P01`支持材料清单，`[C2] → D01-P01`支持30天，`[C3] → D02-P01`支持15天；三个引用各自包含逐字正文、版本日期和同一指纹。冲突保留双方，不在回答代码里按问题或日期选择数字。系统指令要求读取双方并补查替代/生效依据；明示替代且已生效可直接解释，未来生效不提前适用。真实模型是否遵从这些指令留给真实验收。

`gaps`单列未消解冲突、资料缺失和范围边界，不能用工具错误冒充资料未覆盖。`clarification`仅为null或一个关键追问；程序拒绝数组和含多个问号的字符串，纯范围外问题不能追问。无问号的多重请求仍需语义核查，不能声称字符检查证明追问只有一个。

业务结果可同时保留已答材料和未解决部分，示例分别见[材料+缺失](../examples/batch-5/insufficient_evidence.json)、[材料+天气](../examples/batch-5/out_of_scope.json)。执行中断无合法finish时由程序返回`incomplete`，不再调用模型收尾；`citations`不伪造结论引用，`evidence`保留已读原文、出处和指纹，`execution_issues`单列实际执行原因，见[中断运行](../examples/batch-5/interrupted.json)。若合法结果后的Trace保存超时，提升整体为incomplete并保留已有回答和引用。

完整固定语义预期见[用例预期](../examples/batch-5/expectations.json)；本批测试与适用边界见[验证记录](../examples/batch-5/verification.md)。锚点仍只保留提议并明确告警，第6批再校验持久化，本批不宣称记忆有效。

## 第六批会话与上下文

`SessionStore(settings.sqlite_path)`建立SQLite文件，三个表分别为`sessions`（完整锚点、有效位和告警）、`runs`（请求/会话/预留消息ID、running/completed/abandoned状态、完整结果JSON）、`messages`（原始用户文本和完整业务助手消息，按sequence排序）。完整结果与Trace保存于runs，近期历史只使用业务消息，避免把嵌套Trace和旧上下文反复送进模型。助手业务消息包含status、part_statuses、answer、citations、gaps、clarification、execution_issues、memory_warning；不压缩或改写这些内容。

`ConversationService(store, agent_factory).run(session_id, question)`是供后续API调用的内部入口。factory每任务取得同一套资料/索引快照并创建Agent。按数据库路径和会话ID共享进程内锁，同会话顺序执行；数据库连接只存在于短事务，模型等待时没有写事务。不同会话的消息、来源ID和锚点分开读取；没有多进程协调承诺。

开始请求时先短事务提交旧锚点失效，再短事务登记用户消息和running请求。即使登记用户消息失败，也不回滚到已停用的旧锚点。此前有效的快照仅作为本轮输入的`memory_update.before`使用；中途崩溃后磁盘有效位已关闭，重启读取不会启用旧快照。下一请求把遗留running标记为abandoned，未配对用户消息保留，但不强行拼接到其他轮次。正常结束用一个短事务原子提交助手消息、完整结果、新快照或无效状态。

若存储在读取或提交失效前发生故障，跨仓储实例共享的进程内quarantine标记立即停用该会话旧锚点，`memory_warning=storage_uncertain`。下一轮恢复访问时先按无效状态组装上下文，再正常登记并写入持久失效状态；只有成功提交新的结果/锚点状态后清除隔离标记。整个进程在任何新状态都写不进数据库时退出，无法持久保存该次未知请求，这一限制不伪称已恢复。

存储错误返回整体incomplete和`execution_issues: storage_failed`；`persistence`分别声明`saved、user_message_saved、result_saved`。保存失败时保留已有回答、证据和Trace，`memory_valid=false、memory_persisted=false`，不宣称记忆更新成功。首次数据库不可访问、尚未登记的请求不触发模型；无法写入的请求不能声称已持久化。仓储抛出安全StorageError，不把路径或SQLite底层错误发给模型。未知会话抛SessionNotFound，HTTP映射留第七批。

历史预算默认`QA_HISTORY_TOKEN_BUDGET=8000`。`select_history`从最新completed完整问答向前选，按`ceil(UTF-8序列化消息字节数/3)+8/消息`估算；遇到下一轮超预算就停止，不跳过它再捡更早短消息。所选轮次按时间顺序送入，消息ID随原始内容传递。`history_selection`记录预算、估算方法/数量、selected_message_ids和omitted_message_ids；SQLite完整记录不因窗口裁剪删除。当前问题另行放一次，锚点、系统指令、本轮工具观察不算入这8000历史预算，不截断它们。

每个model_request另记整个输入及工具定义的估算量，model_response的`input_calibration`记录该估算、服务返回的actual_prompt_tokens及actual_to_estimate_ratio；usage未知保持null。这是可供校准的数据，不是精确tokenizer或已完成真实校准的声明。本批只测试已知/未知usage字段；真实provider用量对照留真实运行。必要上下文超出模型容量时，模型适配器的明确失败进入incomplete，不通过截断当前问题重试，也没有新增独立问题字符上限。

`anchor_snapshot`仅含subject、focus、pending_clarification三字段，必须完整提交；每项为null或`{value, source_message_ids}`。value为非空字符串，source_message_ids为唯一、非空的本会话消息ID列表，可指本轮用户消息和预留助手消息；公司文档/片段ID、未知及其他会话ID均拒绝。本轮消息ID通过系统上下文提供。完整快照替换，允许全部null；来源存在不证明value语义正确，指令要求换题/纠正更新对象、清除过时事项，追问解决后置空，不存制度答案、原文或员工画像。

业务合法、锚点非法时保留业务状态和引用，只拒绝锚点，记录memory_warning，不消耗格式修正，不使用旧锚点回退。没有合法finish时不接受任何锚点；失联、超时、上限或格式修正失败都停用旧值。下一轮只提供近期历史和null锚点，等待合法重建。同次finish校验不新增模型或记忆工具调用。`anchor_snapshot_proposal`保留原提议供审查，`anchor_snapshot`为接受值；`memory_update`和Trace记录更新前后，`memory_valid`表示校验有效，`memory_persisted`仅在成功提交会话事务后成立。直接调用无会话的Agent会明确session_memory_unavailable。

总deadline覆盖锁等待、会话读取、模型循环和结果保存；SQLite等待受剩余时间限制，并在提交前再次检查，超时回滚，不使用后台线程迟到发布数据库写入。整个任务超时而无法保存结果时，先前已提交的用户消息/running标记仍保留，旧锚点仍无效。数据库完全无法写入时不能承诺保存任何新状态；错误明确返回，不把不确定存储当成功。

长输入估算和私有请求拷贝后再次检查deadline并重算单次timeout；已过期则不计为模型尝试，也不发起模型请求。

实际重启续问、跨窗口、失效/重建和存储失败记录见[第六批验证](../examples/batch-6/verification.md)。这些是受控Mock的工程证据，真实模型的对象理解、纠正与旧结论污染仍需第8.4单独验证。

## 第七批REST接口

`api.create_app(settings)`初始化会话仓储和检索store，创建`ConversationService`，每次问答只acquire一次索引快照并创建同模式Agent。`server`入口显式读取env文件，在127.0.0.1启动单进程Uvicorn，端口默认8000；配置/本地权重/资料/存储准备失败明确退出，不切换模式。普通接口不提供故障注入、模式覆盖或客户端历史参数。测试才可在app工厂中注入依赖。

| 路由 | 当前请求与响应 |
| --- | --- |
| POST /sessions | 可无Body、null或`{}`，201返回session_id和mode；额外字段422 |
| POST /sessions/{id}/messages | 只接收`{"question":"非空原始文本"}`，服务端加载历史/锚点，正常任务200返回完整结构化结果及Trace |
| GET /sessions/{id} | 返回messages（原始用户文本、结构化助手业务消息）、requests（状态及完整已存结果/Trace）、有效锚点与告警；未完成请求result为null |
| GET /health | 返回初始化状态、模式、资料指纹；不创建或调用生成模型，不证明外部模型可达 |

API路由使用同步函数，由FastAPI调度到线程池，复用已有会话内锁和短事务；模型等待不占用事件循环或SQLite写事务。所有引用、预算、deadline、一次恢复/修正及锚点降级仍在同一Agent/ConversationService内执行。没有额外API记忆调用或固定前置改写。

422统一`error.code=invalid_request`，拒绝非法JSON、空白/非字符串question和额外字段，不回显原始输入；404为unknown_session。创建/读取存储失败返回503/storage_failed；问答保存失败503同时附result，保留incomplete、证据、Trace和persistence.saved=false。模型/工具/超时/上限等已进入任务的失败仍200，业务status=incomplete并单列execution_issues。完整结果和Trace已随会话事务保存在SQLite，GET可核对；QA_TRACE_PATH保留给独立执行器显式文件保存，不额外复制出一个可能不同步的API结果文件。

显式Mock默认使用`demo_policy`：只有导出格式、分辨率和报销材料三组受控动作，检索后按演示所需词选择候选、实际read并逐字展示，不能证明真实Query Rewrite或语义决策。无产品对象时追问，不支持的输入明确未执行语义判断并incomplete；不硬编码MP4、1080p或制度期限。规则冲突等真正业务行为仍由live模型和后续真实验收验证。live用现有官方DeepSeek及本地BGE，不在失败时启用此策略。

安装、Mock/live启动、PowerShell中文请求及错误示例见[README](../README.md)。第七批实际进行了进程内API集成、真实loopback HTTP服务启动/两轮问答/隔离/进程重启，以及同一请求的PowerShell UTF-8验证；证据见[验证记录](../examples/batch-7/verification.md)。这不是全新环境测试，也没有执行真实HTTP付费问答。
