# 真实业务问答与失败回归

使用真实DeepSeek和CPU BGE，验证六类核心、规则变体、记忆和资料差分。该历史源码最终四组36轮满足固定预期；原始104轮尝试与343次模型调用均保留，不能将早期名为final的目录直接视为最终通过。

真实运行发现裸引用标记、多追问、临时按15天建议和补查未读新候选等问题。修复引用schema与反馈、回答范围、冲突约束和已读/未读证据提示后，在新目录复跑。失败和修复说明保留在独立审阅报告中。

资料修改实验由独立AI代理先提出MOV→WEBM和预期，再执行与核查；引用审阅同样由AI执行，不计为候选人手工操作。该版本费用已知估算3.333384元，非实际账单。后续记忆修复后的40轮见[当前业务回归](../batch-11/verification.md)。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 最终组 | 实际轮次 / 模型尝试 | 已知保守估算（元） | 覆盖 |
| --- | --- | --- | --- |
| [core-validated](runs/core-validated/summary.json) | 18 / 58 | 0.574484 | 六类各独立两次，含A03和A06双子场景、两次完整两轮追问 |
| [regressions-validated](runs/regressions-validated/summary.json) | 9 / 36 | 0.380280 | 单D01/加入D02、生效/未来日期、三类部分结果、用户偏好、4K正文 |
| [memory-validated](runs/memory-validated/summary.json) | 7 / 21 | 0.197146 | 跨窗对象、换题、纠正、旧1080p历史与4K新正文 |
| [personal-validated](runs/personal-validated/summary.json) | 2 / 6 | 0.056706 | 独立代理预先提出MOV→WEBM，隔离重载，同会话核查新引用 |
| 最终四组小计 | 36 / 121 | 1.208616 | 未知usage 0；不是统计稳定性或泛化保证 |

## 原始证据

- [cases.json](cases.json)
- [core-validated](runs/core-validated/summary.json)
- [regressions-validated](runs/regressions-validated/summary.json)
- [memory-validated](runs/memory-validated/summary.json)
- [personal-validated](runs/personal-validated/summary.json)
- [完整逐项矩阵](delegated-audit/validated-review.md)
- [运行前预期](personal/proposal-before-run.md)
- [独立核查](personal/result-review.md)
- [离线复核脚本](personal/verify_personal.py)
- [core-initial](runs/core-initial/summary.json)
- [初跑报告](delegated-audit/core-initial-review.md)
- [core-repair-1](runs/core-repair-1/summary.json)
- [第一轮修复审阅](delegated-audit/core-repair-1-review.md)
- [core-final](runs/core-final/summary.json)
- [regressions-final](runs/regressions-final/summary.json)
- [补查修复前审阅](delegated-audit/pre-guidance-review.md)
- [定向真实检查](runs/conflict-guidance-check/summary.json)
- [120项离线测试](offline-tests.txt)
- [evidence-index.json](evidence-index.json)
- [56项最终文件指纹](source-fingerprints.json)
- [39项安装包版本](environment-packages.json)
