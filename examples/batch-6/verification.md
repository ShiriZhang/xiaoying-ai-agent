# 第六批实际验证

日期：2026-10-29，America/New_York。范围6.1–6.5，基线提交`20084f152716ab2cb5b3c1b2a9ff48630fb6134a`。AI完成实现、测试和记录；未记录用户个人运行或真实语义核查。本批没有DeepSeek调用和真实BGE加载，生成费用0元；HTTP路由、真实记忆语义及完整业务验收尚未完成。

## 环境与命令

沿用Windows、CPython 3.12.13隔离`.venv`、声明的锁定依赖；新增SQLite来自Python标准库，无新第三方依赖。

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache/uv'
uv sync --offline --locked --extra embedding --no-editable --python .venv/Scripts/python.exe --reinstall-package enterprise-knowledge-qa
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-6/capture_mock.py
openspec validate enterprise-knowledge-qa --strict
```

实际最终全量108项测试通过，报告见[offline-tests.txt](offline-tests.txt)；OpenSpec严格校验通过，uv pip check检查27包兼容。测试从安装包导入业务代码；捕获脚本仅导入仓库tests里的受控策略，业务实现不依赖测试目录。数据库位于测试临时目录，运行后关闭并清理，仓库保存JSON证据，不提交运行数据库。

## 实际记录

| 记录 | 实际工程结果 |
| --- | --- |
| [首轮](first-round.json) | 检索、读取D09、同次finish提出锚点，3模型/2工具，无额外记忆调用，保存成功 |
| [重启续问](restarted-follow-up.json) | 重开SQLite文件，历史预算冻结为1以触发跨窗；selected_message_ids为空，仍提供合法对象锚点，并重新检索/读取D10 |
| [非法锚点](invalid-anchor.json) | 未知消息来源被拒，业务out_of_scope保留，格式修正0，memory_valid=false |
| [模型故障](model-failure.json) | incomplete，旧锚点不启用，无伪造更新，故障结果本身保存成功 |
| [锚点重建](rebuilt-anchor.json) | null旧锚点、近期历史输入后同次finish重建结构合法锚点；受控动作主动提交incomplete业务状态，记忆校验独立，二者不混同 |
| [SQLite保存失败](storage-failure.json) | 真实SQLite触发器拒绝助手写入，事务回滚，已有用户消息保留，结果saved=false，memory_valid=false |
| [最终持久化状态](persisted-state.json) | 完整原始业务消息仍在，最后请求running且只有用户消息，旧锚点无效；没有伪造已保存助手 |

这些是实际执行器与SQLite运行，但模型为受控Mock。跨窗测试证明锚点输入、独立read-set和重启接线；不能据此断言真实模型理解、提取或清空锚点正确。完整配置、输入、快照指纹、来源消息ID、更新前后、历史选取、计数、usage和Trace在各JSON中。运行期日期/时区取执行器时钟，文件保存实际值；本节记录使用用户所在日期。

## 测试覆盖

新增22项测试：会话8项、上下文6项、记忆5项、失败3项。除上述记录，还验证同会话多个仓储实例顺序执行、模型等待时另一真实SQLite写入可提交、登记失败不调用模型、不谎称用户消息已存、初始化错误/未知会话、全部历史与来源隔离。

历史窗口测试包含精确边界、完整轮次、不越过最近大轮次拾取旧短轮次、原文顺序、未配对消息遗漏记录、长当前问题只出现一次、本轮工具观察不裁剪。估算为`ceil(序列化UTF-8消息字节数/3)+8/消息`，默认8000；每次模型请求的完整输入估算与返回usage留校准字段。已知usage来自受控测试，未知保持null，未宣称已用真实provider校准。

记忆测试包含本会话历史、窗口外来源、本轮助手预留ID，未知/跨会话/文档ID拒绝，完整快照、换题/纠正、清空待澄清项。业务合法且仅锚点错时不触发格式修正、不丢回答；无合法finish的模型失联、60/300秒、工具上限和修正失败均停用旧锚点。SQLite提交前过期会回滚，没有后台迟到写入。隔离替换1080p为4K后，历史存在旧答案也不能授予本轮引用权限；先拒绝未读引用，再实际读新原文修正成功，不更改基础语料。

## 失败与修复

- 首次6项会话测试中，2项业务断言已通过，但测试清理SQLite文件遭Windows占用错误。原因是测试的`with sqlite3.connect(...)`只管理事务，不关闭连接；改用显式closing并提交触发器后6项通过。
- 实现复核发现若把旧锚点失效与用户登记放同一事务，登记故障会一并回滚失效标记。改为先短事务提交失效，再登记用户；回归检查已有有效锚点在登记失败后仍无效。
- 后续完整106项测试和捕获脚本通过，无新依赖、业务规则或验收标准变更。
- 代码审查规范轴发现长输入估算后未重查deadline：修复为估算与拷贝后复查、重算timeout再计数。新增回归确认剩20秒时单次timeout=20，估算推进301秒时没有模型调用或计数。
- 代码审查规格轴发现失效提交前的瞬时读/写失败后可能重启用旧锚点：增加跨仓储实例共享quarantine，恢复时先隔离旧值、成功提交新状态后清除。新增回归用一次读错误及真实SQLite触发器拒绝失效UPDATE验证，数据库旧有效位仍为1时仓储仍报告不可用、下一轮before为null。
- 修复后重新安装源码，最终108项测试通过；捕获脚本全部复跑，证据对应最终源码。额外包兼容检查首次误用不可写的默认uv缓存而失败，改用上述项目缓存后27包兼容。

## 限制与后续

只提供进程内同会话顺序，不承诺多进程协调。必要输入超模型容量时保留完整输入并明确失败，不通过裁剪当前问题隐藏；本批容量失败用受控模型错误验证。数据库完全不能写入时不可能承诺保存新状态，返回存储错误，不伪称保存成功。只有先前已成功登记/失效的状态能在重启后可靠恢复。

结构与消息来源合法不代表锚点语义正确；字段不应承载企业答案/原文/画像由指令约束，真实语义留第8.4。不将本批工程通过替代真实六类场景、个人先预测再修改及冷启动验收。

最终源码、测试和捕获脚本指纹见[source-fingerprints.json](source-fingerprints.json)，采用UTF-8/LF归一化SHA-256。个人工时未推算。规划与任务状态按既有规则仅本地保存。

## Standards

按code-review技能独立只读审查非空候选`git diff --cached 20084f1`（用户要求审查后才提交，当时基线后commit列表为空），依据项目文档约定及技能smell baseline。初次1项P2：输入估算耗尽deadline后仍可能请求模型。修复为估算和私有输入拷贝后重新检查与计算timeout，回归覆盖剩20秒和过期零调用。代理复核确认解决，未发现新问题或需修改的判断性smell。

## Spec

另一个独立只读代理按用户指定OpenSpec和docs/01审查6.1–6.5。初次1项P2：失效提交前的瞬时存储失败可能使下一轮恢复旧锚点。共享quarantine与读/失效写失败回归修复后，代理确认跨仓储实例仍停用旧锚点、before=null，未引入新问题。HTTP路由和真实语义层按原规划待后续任务，未误报为本批已完成。

最终待修问题：Standards 0，Spec 0。两轴最严重的初次问题均为P2且已解决。最终108项离线测试通过、记录复跑、27包兼容与OpenSpec严格校验通过；本批审查不代替真实语义验收。
