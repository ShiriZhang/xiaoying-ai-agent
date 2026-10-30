# 历史独立验收：记忆边界缺陷

验收对象为历史版本e1e9ef2cd5376afd68aea7b38c36c755d2dbbfcc。六类核心样本及50处引用核对有支持，但发现有效锚点focus保存“15天与30天规定冲突”，违反仅保留讨论事项的约束。

该锚点有合法字段与来源，仍会带入后续系统上下文；没有观察到其已经导致错误业务答案，不能将其升级为已发生的无依据回答。此发现说明测试全绿和引用来源合法不足以证明记忆语义正确。

后续修复覆盖新旧快照、正反例与同会话资料重载，见[修复回归](../batch-11/verification.md)。个人贡献与学习说明以[AI使用记录](../../docs/04-ai-usage.md)和[复盘](../../docs/05-retrospective.md)为准。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 检查 | 该次实际结果 | 证明范围 |
| --- | --- | --- |
| 全部工程/API测试 | [120项通过，0失败/错误/跳过](tests.txt)，7.224秒 | 配置、工具、预算、deadline、引用、SQLite、历史/锚点与API工程契约 |
| 实际Mock HTTP及PowerShell请求 | [13次请求](http.json)、[PowerShell](powershell.json)，两轮、隔离及进程重启通过 | 实际服务与持久化，禁止外部连接/BGE构造，不证明真实语义 |
| 真实本地CPU BGE | [14项召回及重载边界通过](real-retrieval.json)，17.25秒，无缺失 | 真实编码与BM25/RRF、6/12候选、单D01/加入D02、正文替换及长输入拒绝；无生成API调用 |
| 当前源码与历史真实运行一致性 | [审计通过](delivery-audit.json) | 安装包、当前src、四组、两空环境及真实HTTP指纹一致，前批56项输入文件未变 |
| 真实生成语义与引用复核 | 独立重新阅读已有36轮，[50处引用来源核对全部一致](business-evidence.json) | 原文、文档ID、版本、指纹和该次read-set一致；语义结论通过实际阅读核查 |
| 干净环境安装与真实权重独立准备 | 复核[原始证据](../batch-9/verification.md) | 该次没有重新安装第三个环境或重新下载权重，不冒称再次完成冷启动 |

| 场景 | 独立核查结论 | 真实记录入口 |
| --- | --- | --- |
| 明确答案 | 通过；发票和出差审批单，附加审批流有独立出处，没有附带单侧期限 | core-validated的A01，两次 |
| 文档冲突 | 通过业务结果；双方原文→补查→读取新相关候选，列30/15冲突并请求适用依据，未擅选15天 | core-validated的A02，两次 |
| 资料外问题 | 通过；住房补贴为资料未覆盖，未声称公司无补贴；天气说明范围 | A03-missing/A03-weather，各两次 |
| 改写后的相似问题 | 通过；口语改写仍给相同两项材料及该次原文 | A04，两次 |
| 上下文追问 | 通过已测业务；先格式再分辨率，该次重新读D10、回答1080p | A05，每次两轮、两次独立会话 |
| 工具失败 | 通过；真实模型观察临时/持续read错误，至多一次恢复，持续失败明确incomplete | A06-temporary/A06-persistent，各两次 |

## 原始证据

- [报告](../batch-11/verification.md)
- [120项通过，0失败/错误/跳过](tests.txt)
- [13次请求](http.json)
- [PowerShell](powershell.json)
- [14项召回及重载边界通过](real-retrieval.json)
- [审计通过](delivery-audit.json)
- [50处引用来源核对全部一致](business-evidence.json)
- [原始证据](../batch-9/verification.md)
- [原始36轮矩阵](../batch-8/delegated-audit/validated-review.md)
- [conversation-memory规格](../../docs/specs/conversation-memory.md)
- [A02第一次真实结果](../batch-8/runs/core-validated/A02-r1-t1-97edf89e80624707aca3cc60ae44fcf3.json)
- [加入D02的结果](../batch-8/runs/regressions-validated/added-D02-r1-t1-32e8f710050e4d1d99241ff6e02b65fd.json)
- [复盘文档](../../docs/05-retrospective.md)
