# 验证证据导航

先阅读[效果验证](../docs/03-evaluation.md)了解预期、实际结果和证明边界，再按下表核查原始输入、输出与Trace。目录编号仅作为已有文件定位，评估以对应源码、资料指纹和运行配置为准。

| 检查内容 | 入口 |
| --- | --- |
| 当前完整79场景 | [验收矩阵](batch-11/acceptance-matrix.md) |
| 最终真实40轮 | [回归说明](batch-11/verification.md)、[逐轮索引](publication-review-2026-10-30/business-evidence.json) |
| 124项测试 | [测试输出](publication-review-2026-10-30/tests.txt) |
| 实际HTTP与PowerShell | [HTTP](acceptance-final-2026-10-29/http.json)、[PowerShell](acceptance-final-2026-10-29/powershell.json) |
| 真实CPU检索与重载 | [检索结果](acceptance-final-2026-10-29/retrieval/f619369b806944b4b1a8643afdd1d910.json) |
| 独立环境、权重与真实HTTP | [复现报告](batch-9/verification.md) |
| 原始语义失败及修复 | [初次审阅](batch-8/delegated-audit/core-initial-review.md)、[补查问题](batch-8/delegated-audit/pre-guidance-review.md) |
| 记忆旧结论问题 | [原失败索引](batch-11/baseline-failures.json)、[修复与复验](batch-11/verification.md) |
| 独立AI资料变更实验 | [预期](batch-8/personal/proposal-before-run.md)、[实际核查](batch-8/personal/result-review.md) |

失败、工具错误和服务中断保留原始记录。较早报告对应其当时版本，不用其测试数量或业务结论覆盖最终版本；机械检查与语义核查分别解释。所有资料为虚构合成内容，不包含真实密钥、认证头或隐私数据。
